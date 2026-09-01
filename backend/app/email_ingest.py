"""
Ingesta de eventos de salud desde una bandeja de Gmail "pasarela".

Flujo: el usuario reenvia el correo de su laboratorio/EPS a una direccion de
Gmail dedicada solo para esto (nunca su correo personal). Esta bandeja se
revisa por IMAP -- ni Claude ni la app necesitan una URL publica ni un
proveedor de correo entrante de pago para esto, a diferencia del diseno
original con webhooks (ver docs/ARQUITECTURA.md).

Seguridad / privacidad:
- Solo se procesan correos cuyo remitente coincida exactamente con el correo
  registrado de algun paciente existente (Patient.email) -- cualquier otro
  correo que llegue a la bandeja (spam, promociones) se ignora sin llamar a
  la IA.
- Nunca se guarda la contrasena real de Gmail: se usa una "contrasena de
  aplicacion" (App Password), configurable y revocable desde la cuenta de
  Gmail sin afectar el acceso normal a esa cuenta.
- La confirmacion humana sigue siendo obligatoria: esto solo crea filas en
  PendingEmailEvent, nunca HealthEvent directamente -- ver routers/correo.py.
"""
import base64
import email
import html
import imaplib
import json
import re
from email.header import decode_header
from email.utils import parseaddr

from sqlalchemy.orm import Session

from . import config, crud
from .ai_extract import (
    AIExtractionError,
    ALLOWED_MEDIA_TYPES,
    ALLOWED_PDF_MEDIA_TYPES,
    extract_health_event_from_email_text,
    extract_health_event_from_image,
    extract_health_event_from_pdf,
)

# Umbral minimo de caracteres del cuerpo de texto para molestarse en llamar a
# la IA -- cuerpos mas cortos que esto casi siempre son firmas o "ver adjunto".
MIN_BODY_CHARS = 30


class EmailIngestError(Exception):
    """Fallo de conexion/autenticacion con la bandeja de Gmail (no de la IA)."""


def _conectar() -> imaplib.IMAP4_SSL:
    """Punto de extension para pruebas: se puede reemplazar con un mock."""
    conexion = imaplib.IMAP4_SSL("imap.gmail.com")
    conexion.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
    return conexion


def _decode_subject(raw_subject: str | None) -> str:
    if not raw_subject:
        return ""
    partes = decode_header(raw_subject)
    resultado = []
    for texto, codificacion in partes:
        if isinstance(texto, bytes):
            resultado.append(texto.decode(codificacion or "utf-8", errors="replace"))
        else:
            resultado.append(texto)
    return "".join(resultado)


def _html_a_texto(html_content: str) -> str:
    sin_tags = re.sub(r"<[^>]+>", " ", html_content)
    return html.unescape(re.sub(r"\s+", " ", sin_tags)).strip()


def _extraer_cuerpo_y_adjuntos(msg: email.message.Message) -> tuple[str, list[dict]]:
    """Devuelve (cuerpo_texto, [{"filename", "media_type", "bytes"}])."""
    cuerpo_plain = ""
    cuerpo_html = ""
    adjuntos: list[dict] = []

    if msg.is_multipart():
        partes = msg.walk()
    else:
        partes = [msg]

    for parte in partes:
        if parte.is_multipart():
            continue
        content_type = (parte.get_content_type() or "").lower()
        disposicion = (parte.get_content_disposition() or "").lower()
        filename = parte.get_filename()

        es_adjunto = disposicion == "attachment" or (filename and disposicion != "inline")
        if es_adjunto and (content_type in ALLOWED_PDF_MEDIA_TYPES or content_type in ALLOWED_MEDIA_TYPES):
            payload = parte.get_payload(decode=True)
            if payload:
                adjuntos.append({"filename": filename or "adjunto", "media_type": content_type, "bytes": payload})
            continue

        if disposicion == "attachment":
            continue

        if content_type == "text/plain" and not cuerpo_plain:
            payload = parte.get_payload(decode=True)
            if payload:
                charset = parte.get_content_charset() or "utf-8"
                cuerpo_plain = payload.decode(charset, errors="replace")
        elif content_type == "text/html" and not cuerpo_html:
            payload = parte.get_payload(decode=True)
            if payload:
                charset = parte.get_content_charset() or "utf-8"
                cuerpo_html = payload.decode(charset, errors="replace")

    cuerpo = cuerpo_plain.strip() or _html_a_texto(cuerpo_html)
    return cuerpo.strip(), adjuntos


def _paciente_por_remitente(db: Session, remitente: str):
    remitente_normalizado = remitente.strip().lower()
    if not remitente_normalizado:
        return None
    for patient in crud.list_patients(db):
        if patient.email and patient.email.strip().lower() == remitente_normalizado:
            return patient
    return None


def revisar_bandeja_entrada(db: Session) -> dict:
    """
    Revisa la bandeja de Gmail pasarela en busca de correos no leidos,
    procesa los que vienen de un remitente reconocido (Patient.email) y crea
    un PendingEmailEvent por cada adjunto/cuerpo con informacion util.

    Devuelve un resumen para mostrarle al usuario, nunca lanza excepciones
    de conexion/IMAP hacia afuera (las captura y las devuelve en "error").
    """
    if not config.EMAIL_INGEST_CONFIGURED:
        return {
            "ok": False,
            "error": "La bandeja de correo pasarela todavia no esta configurada (faltan "
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD en el archivo .env).",
        }

    try:
        conexion = _conectar()
    except Exception as exc:
        return {"ok": False, "error": f"No se pudo conectar a la bandeja de Gmail: {exc}"}

    revisados = 0
    nuevos_pendientes = 0
    no_reconocidos = 0

    try:
        estado, _ = conexion.select("INBOX")
        if estado != "OK":
            return {"ok": False, "error": "No se pudo abrir la bandeja de entrada de Gmail."}

        estado, datos = conexion.search(None, "UNSEEN")
        if estado != "OK":
            return {"ok": False, "error": "No se pudo buscar correos nuevos en la bandeja."}

        ids = datos[0].split() if datos and datos[0] else []

        for msg_id in ids:
            revisados += 1
            try:
                estado, msg_data = conexion.fetch(msg_id, "(RFC822)")
                if estado != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw_bytes = msg_data[0][1]
                msg = email.message_from_bytes(raw_bytes)

                remitente_nombre, remitente_email = parseaddr(msg.get("From", ""))
                asunto = _decode_subject(msg.get("Subject"))
                fecha = msg.get("Date", "")

                patient = _paciente_por_remitente(db, remitente_email)
                if patient is None:
                    no_reconocidos += 1
                    continue

                cuerpo, adjuntos = _extraer_cuerpo_y_adjuntos(msg)

                for adjunto in adjuntos:
                    media_type = adjunto["media_type"]
                    es_pdf = media_type in ALLOWED_PDF_MEDIA_TYPES
                    try:
                        if es_pdf:
                            extraido = extract_health_event_from_pdf(adjunto["bytes"])
                        else:
                            extraido = extract_health_event_from_image(adjunto["bytes"], media_type)
                        error_texto = None
                    except AIExtractionError as exc:
                        extraido = None
                        error_texto = str(exc)

                    crud.create_pending_email_event(
                        db,
                        patient_id=patient.id,
                        email_subject=asunto or adjunto["filename"],
                        email_from=remitente_email,
                        email_date=fecha,
                        preview_type="pdf" if es_pdf else "image",
                        preview_content=base64.standard_b64encode(adjunto["bytes"]).decode("ascii"),
                        preview_media_type=media_type,
                        extracted_json=json.dumps(extraido) if extraido is not None else None,
                        error=error_texto,
                    )
                    nuevos_pendientes += 1

                if len(cuerpo) >= MIN_BODY_CHARS:
                    try:
                        extraido = extract_health_event_from_email_text(asunto, cuerpo)
                    except AIExtractionError as exc:
                        extraido = None
                        error_texto = str(exc)
                    else:
                        error_texto = None

                    if extraido is not None or error_texto is not None:
                        crud.create_pending_email_event(
                            db,
                            patient_id=patient.id,
                            email_subject=asunto,
                            email_from=remitente_email,
                            email_date=fecha,
                            preview_type="texto",
                            preview_content=cuerpo,
                            preview_media_type=None,
                            extracted_json=json.dumps(extraido) if extraido is not None else None,
                            error=error_texto,
                        )
                        nuevos_pendientes += 1
            finally:
                # Se marca como leido siempre (haya coincidido o no) para no
                # reprocesar el mismo correo en cada revision.
                conexion.store(msg_id, "+FLAGS", "\\Seen")
    except Exception as exc:
        return {"ok": False, "error": f"Fallo revisando la bandeja de Gmail: {exc}"}
    finally:
        try:
            conexion.logout()
        except Exception:
            pass

    return {
        "ok": True,
        "error": None,
        "mensajes_revisados": revisados,
        "pendientes_nuevos": nuevos_pendientes,
        "no_reconocidos": no_reconocidos,
    }
