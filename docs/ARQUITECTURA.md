# Arquitectura y hoja de ruta

> Hoja de ruta visual (para compartir o revisar rápido): ver el artefacto
> "Hoja de Ruta: Salud y Deporte" publicado en la conversación de Cowork.
> Este archivo es la versión técnica de referencia, la que vive con el código.

## Fase 0 — Fundación (completada, 28/08/2026)

**Objetivo:** tener tus datos de salud organizados, editables y consultables, en una app que
corre localmente, con una base de datos propia y una API sobre la cual se puede construir todo
lo demás.

**Decisiones de diseño:**

- **Backend en Python con FastAPI.** Framework moderno, tipado, con documentación
  interactiva automática (`/docs`), fácil de mantener y de que tú mismo participes en el
  código dado que ya conoces Python.
- **Base de datos con SQLAlchemy + SQLite.** SQLite no requiere instalar ni configurar nada
  (es un solo archivo, `salud_deporte.db`). El código de acceso a datos no depende de SQLite
  en particular — cambiar a Postgres para producción es solo cambiar la variable de entorno
  `DATABASE_URL`, sin tocar `models.py`, `crud.py` ni los routers.
- **Un modelo de datos genérico (`HealthEvent`) en vez de siete tablas rígidas.** Cada evento
  de salud (una condición, un medicamento, un resultado de laboratorio, etc.) se guarda con la
  misma forma: fecha, categoría FHIR, título, detalle, valor, rango de referencia, institución,
  fuente. Esto tiene dos ventajas: (1) coincide con la hoja de cálculo cronológica que ya usas
  como referencia, y (2) facilita que un futuro motor de correlación de IA pueda recorrer todos
  los eventos de un paciente de manera uniforme, sin siete consultas distintas.
- **Separación API / interfaz web.** Las rutas bajo `/api/...` devuelven JSON y son las que
  usaría cualquier otra aplicación (una futura app móvil, una integración con una institución,
  el motor de IA). Las rutas bajo `/`, `/eventos`, etc. renderizan HTML para que tú puedas usar
  la app directamente desde el navegador, sin depender de que exista un frontend aparte.

**Estado:** app funcional, precargada con tus 58 eventos reales, repo git local inicializado.

---

## Fase 1 — Ingesta desde foto (primera versión lista, 28/08/2026)

**Objetivo:** que suministres la foto de un examen o documento, y la app extraiga los datos e
incorpore el evento — sin transcripción manual y sin guardar nada sin tu confirmación.

**Decisión técnica — visión de Claude en vez de OCR tradicional:** el plan original
contemplaba `pytesseract` (OCR) + un paso separado de estructuración con IA. Se simplificó a
un solo paso: la foto se manda directamente a un modelo de Claude con capacidad de visión, que
lee el contenido y devuelve el JSON estructurado en una sola llamada. Esto evita depender de
instalar el motor de Tesseract por separado en Windows, y en la práctica es más preciso para
letra de laboratorio y sellos.

**Flujo implementado:**

1. **`GET /importar`** — formulario para subir una foto (JPEG/PNG/WEBP/GIF, máx. 15 MB). Si no
   hay una `ANTHROPIC_API_KEY` configurada, muestra instrucciones en vez del formulario.
2. **`POST /importar/analizar`** (`routers/ingest.py`) — recibe la imagen, llama a
   `ai_extract.extract_health_event_from_image()`, y renderiza `confirmar_evento.html` con la
   imagen y un formulario prellenado con lo que la IA detectó (categoría FHIR, fecha, título,
   valor, rango de referencia, institución). Si la IA no está segura de algo, lo dice en un
   aviso visible (`notes_for_user`).
3. **Confirmación humana obligatoria** — el formulario de confirmación postea al mismo
   endpoint que ya existía, `POST /eventos/nuevo`; no hay una ruta de guardado "directo" desde
   la IA. El campo "Fuente" queda prellenado como *"Foto analizada con IA — confirmado por el
   paciente"*, editable.

**Configuración:** `ANTHROPIC_API_KEY` (y opcionalmente `ANTHROPIC_MODEL`) se leen de un
archivo `.env` en la raíz del proyecto (ver `.env.example`), cargado por `app/config.py` con
`python-dotenv`. `.env` está en `.gitignore` — la llave nunca se sube al repositorio ni se le
pasa a nadie más.

**Pendiente dentro de esta fase:** soporte para PDF digital (texto ya seleccionable, como los
informes que ya llegan por correo) — se puede sumar como una segunda entrada al mismo
`ai_extract.py` (extraer texto con `pdfplumber` y mandarlo como texto en vez de imagen), sin
cambiar el flujo de confirmación.

**Construido con:** API de Claude (paquete `anthropic`), `python-dotenv`, nuevo router
`routers/ingest.py`, plantillas `importar.html` y `confirmar_evento.html`.

**Riesgo a vigilar:** calidad de la foto (letra borrosa, mala luz) — se mitiga mostrando
siempre la imagen original junto al formulario de confirmación, nunca guardando a ciegas, y
con el aviso `notes_for_user` cuando la IA no está segura de un campo.

---

## Fase 2 — Tendencias en el tiempo (primera versión lista, 28/08/2026)

**Objetivo:** ver la evolución de cualquier prueba (colesterol, glucosa, TSH...) como una
gráfica en el tiempo, no como filas sueltas en una tabla.

**Cómo quedó implementado:**

- `GET /tendencias` — un `<select>` con los títulos de `HealthEvent` que tienen **al menos 2
  eventos con `event_date_sort` no nulo y un `value` interpretable como número**
  (`_chartable_titles()` en `routers/trends.py`). Un evento sin fecha exacta o sin valor
  numérico simplemente no entra a la gráfica — nunca se inventa un punto.
- `GET /api/trends/{title}` — devuelve los puntos ordenados por fecha (`date`, `value`
  numérico, `raw_value` tal como está guardado, `reference_range`, `institution`) más el rango
  de referencia interpretado del registro más reciente que se pudo entender, como
  `[mínimo, máximo]`.
- La página dibuja la serie con Chart.js: la línea de valores, y si hay rango de referencia,
  una banda de fondo (dos datasets con `fill: '-1'`, sin necesidad de un plugin adicional).
  Debajo de la gráfica hay una tabla con los mismos puntos, para quien prefiera los números.
- **Chart.js se sirve localmente** (`backend/app/static/vendor/chart.umd.js`, ~200 KB,
  instalado vía `npm install chart.js` y copiado al repo) en vez de cargarse desde un CDN
  externo — se detectó durante el desarrollo que el entorno de verificación no tenía salida a
  `cdn.jsdelivr.net`, y servirlo local es además más robusto para cualquier usuario detrás de
  un firewall corporativo o sin conexión a ese CDN en particular.
- **Interpretación de texto libre → número** (`app/trends.py`, funciones
  `parse_numeric_value` y `parse_reference_range`): los campos `value` y `reference_range` son
  texto libre tal como aparecen en la fuente original ("190 mg/dL", "0 – 200 (óptimo)",
  "< 3.1 (51–60 años)"). El parser quita paréntesis antes de buscar un rango (para no confundir
  un rango de edad entre paréntesis con el rango de referencia real) y entiende rangos
  "abiertos" tipo "< 3.1" como `(0, 3.1)`. Cuando no puede interpretar algo, devuelve `None` y
  ese punto no se grafica.
- **Limitación conocida y documentada en el código:** el separador de miles en formato
  latinoamericano (p. ej. "6.240" leucocitos) se interpreta igual que un separador decimal
  ("6.24"). Correcto para casi todos los analitos de esta app (colesterol, glucosa,
  creatinina, TSH...), pero subestima recuentos grandes (leucocitos, plaquetas). No se intentó
  resolver la ambigüedad porque los datos de origen mezclan ambas convenciones sin manera
  algorítmica confiable de distinguirlas — queda como mejora futura si se vuelve relevante.
- Caso ya visible en los datos actuales: colesterol total bajando de 265 a 137 mg/dL entre
  jun-2024 y ago-2026, con la banda de referencia (0–200, óptimo) de fondo.

**Pendiente dentro de esta fase:** filtro por rango de fechas (por ahora se grafica todo el
historial disponible de la prueba elegida); unificar títulos equivalentes con nombres
distintos (ej. "Creatinina (suero)" vs. "Creatinina sérica" no se agrupan automáticamente hoy).

**Construido con:** Chart.js (servido localmente), `app/trends.py`, `routers/trends.py`,
consume `/api/events` indirectamente vía `crud.list_events()` (no se tocó el modelo de datos).

---

## Fase 3 — Resumen con IA: interpretación, recomendaciones y alertas (primera versión lista, 01/09/2026)

**Objetivo:** un botón que le pide a la IA leer todo el historial del paciente y devolver un
resumen en lenguaje claro — tendencias relevantes, valores a vigilar, preguntas sugeridas para
el médico — siempre dejando explícito que no reemplaza una evaluación profesional.

**Cómo quedó implementado:**

- **`GET /resumen`** — muestra el formulario ("Generar resumen") con el conteo de eventos del
  paciente activo, o instrucciones si falta configurar `ANTHROPIC_API_KEY`.
- **`POST /resumen/generar`** (`routers/summary.py`) — llama a
  `ai_summary.generate_health_summary(patient, events)`, que arma un prompt en español
  (`ai_summary.PROMPT_INSTRUCTIONS`) pidiendo explícitamente **describir y correlacionar,
  nunca diagnosticar ni prescribir**, con salida en JSON: `resumen_general`, `hallazgos[]`
  (cada uno con `titulo`, `categoria`, `nivel` — importante/atención/informativo —, `detalle`,
  `evidencia` y `marcador`), `sugerencias[]` y `temas_para_el_medico[]`. Reutiliza el mismo
  patrón de cliente/config que `ai_extract.py` (Fase 1).
- **Gráfica por hallazgo:** el campo `marcador` es el título exacto (tal como aparece en el
  historial) del marcador/medición que mejor respalda ese hallazgo. `_build_chart()` /
  `_attach_charts()` en `routers/summary.py` buscan esos eventos, arman los mismos puntos que
  usa `/tendencias` (Fase 2) y los adjuntan al hallazgo para graficarlos con Chart.js — sin
  volver a llamar a la IA para eso.
- **UI de hallazgos:** cada hallazgo se muestra colapsado (título + nivel) y solo al hacer
  click se expande el detalle, la evidencia y la gráfica (`<details>`/`<summary>` nativos, sin
  JS de por medio para el toggle; el `Chart.js` de cada gráfica se dibuja de forma perezosa,
  solo cuando el hallazgo se abre por primera vez).
- **Indicador de carga:** como la respuesta de Claude puede tardar medio minuto o más, la
  página muestra un panel con iconos (corazón con pulso, cronómetro girando via SVG
  `animateTransform`, corredor con animación CSS) y un contador de segundos en vivo, para que
  quede claro que la app sigue trabajando y no se congeló.
- **Todo resumen generado muestra un aviso fijo, no opcional:** "Esto no es un diagnóstico
  médico" — visible siempre en la página, generado el resumen o no.

**Construido con:** API de Claude (mismo cliente que Fase 1), `ai_summary.py`,
`routers/summary.py`, `templates/resumen.html`, reutiliza `app/trends.py` (Fase 2) para
interpretar valores numéricos y rangos de referencia al armar cada gráfica.

**Pendiente dentro de esta fase:** guardar cada resumen generado con fecha (tabla
`AiSummary`, por definir) para poder verlo después sin regenerarlo; exportar el resumen a PDF.

**Cómo probarla objetivamente:** el paciente de prueba Greg Welch (ver más abajo) tiene 6
condiciones sembradas deliberadamente en sus datos, sin ninguna etiqueta diagnóstica visible
para la IA — la respuesta esperada está documentada aparte en
[`ANOMALIAS_PRUEBA_GREG.md`](ANOMALIAS_PRUEBA_GREG.md), para comparar contra lo que la Fase 3
detecta sin haberle dado la respuesta de antemano.

---

## Selector de paciente activo (cookie) — implementado, 01/09/2026

Paso intermedio entre "un solo paciente hardcodeado" (Fase 0) y multiusuario real
(Fase 4): un `<select>` en el header (visible solo si hay más de un paciente cargado) deja
elegir cuál está activo. La elección se guarda en la cookie `active_patient_id` y todas las
páginas (`/`, `/eventos`, `/tendencias`, `/importar`, `/resumen`) leen el paciente activo de
ahí, con `_current_patient()` en `routers/pages.py`. **No es autenticación** — cualquiera que
use el navegador puede cambiar de paciente; sirve para separar tus datos reales del paciente
de prueba mientras se desarrolla, y se reemplaza por login real en la Fase 4.

## Paciente de prueba: Greg Welch — implementado, 01/09/2026

Para poder seguir construyendo y probando funcionalidad (especialmente la Fase 3) sin usar
datos reales, `backend/app/greg_data.py` genera 5 años (2021-2025) de historial sintético de
un triatleta amateur de 40 años con hipotiroidismo: 10 paneles de laboratorio (14
marcadores) y datos mensuales estilo Garmin (VO2max, FC en reposo, HRV, horas de
entrenamiento, sueño, peso), cargados por `seed_greg.py` (idempotente, se salta si el
paciente ya existe). Incluye 3 condiciones de salud y 3 condiciones deportivas sembradas
deliberadamente en los patrones numéricos, sin ninguna etiqueta diagnóstica en los datos —
pensadas como set de prueba ciego para la Fase 3. El detalle completo (valores exactos,
fechas, qué se espera que la IA detecte) está en
[`ANOMALIAS_PRUEBA_GREG.md`](ANOMALIAS_PRUEBA_GREG.md) — deliberadamente no se le da esa
respuesta a la IA antes de evaluarla.

## Fase 4 — Multiusuario, seguridad y despliegue en la nube (planeada, prioridad adelantada 01/09/2026)

Cuando el objetivo pase de "mi app personal" a "una app que otras personas puedan usar", la
seguridad deja de ser opcional: **no se debe abrir esta app a otras personas hasta que estos
puntos estén resueltos**, no solo los de infraestructura.

**Requisitos de seguridad (bloqueantes antes de multiusuario real):**

1. **Autenticación de usuarios** (login, sesiones) — cada usuario ve solo sus propios
   pacientes/eventos. FastAPI tiene soporte maduro para esto (OAuth2/JWT). El selector de
   paciente por cookie (implementado 01/09/2026) es solo una comodidad de desarrollo, **no es
   seguridad** — cualquiera con acceso al navegador puede cambiar de paciente.
2. **Aislamiento por usuario a nivel de base de datos**, no solo de interfaz — una consulta mal
   filtrada no debe poder devolver datos de otro usuario.
3. **Cifrado**: HTTPS siempre en tránsito; cifrado en reposo para la base de datos una vez deje
   de ser un archivo SQLite local en la máquina del propio usuario.
4. **Minimizar qué se envía a la IA y por cuánto tiempo se guarda**, en cualquier canal de
   ingesta (foto, PDF, correo) — mismo principio ya aplicado en la Fase 1: se envía a la API de
   Claude solo para el análisis puntual, no se retiene del lado del servidor más allá de la
   sesión de confirmación.
5. **Revisión legal antes de manejar datos de un segundo usuario real** (no de prueba): en
   Colombia aplica la Ley 1581 de 2012 (habeas data), con especial cuidado por tratarse de
   datos de salud. Esto aplica desde el primer usuario real adicional, no solo al integrarse
   con instituciones (Fase 5).

**Requisitos de infraestructura:**

6. **Migrar la base de datos a Postgres** (Supabase, Railway, RDS, etc.) — un solo cambio de
   variable de entorno, sin reescribir el modelo de datos.
7. **Migraciones de esquema con Alembic**, en vez de `Base.metadata.create_all()` (que solo
   sirve para desarrollo local).
8. **Despliegue** en un servicio como Railway, Render o Fly.io — el mismo código FastAPI corre
   sin cambios, solo se agrega un `Dockerfile`. Necesario, entre otras cosas, para tener una URL
   pública a la que un proveedor de correo entrante pueda reenviar mensajes (ver ingesta por
   correo, abajo).
9. **Frontend dedicado** (opcional, si la interfaz Jinja2 se queda corta): un frontend en React
   o similar que consuma la API `/api/...` ya existente, sin tocar el backend.

## Ingesta por correo / reenvío (implementada 01/09/2026, MVP de un solo usuario)

**Objetivo:** que una persona no técnica pueda cargar sus resultados simplemente reenviando el
correo del laboratorio o la EPS a una dirección personal — sin fotografiar nada, sin llenar
formularios. Es, en la práctica, el canal de menor fricción posible: la mayoría de resultados
ya le llegan a la gente por correo.

**Diseño implementado — más simple que el diseño original con webhooks (ver historial de este
archivo si hace falta la versión anterior):** en vez de necesitar hosting público con URL propia
y un proveedor de correo entrante de pago (Mailgun/Postmark/SendGrid, que requerían dominio
propio y una cuenta externa), la app usa una bandeja de **Gmail dedicada** ("pasarela") que
revisa por **IMAP** — protocolo estándar de lectura de correo, sin webhooks:

1. Se crea una cuenta de Gmail nueva, separada de cualquier correo personal, dedicada solo a
   recibir estos reenvíos (ej. `misregistros.<algo>@gmail.com`).
2. El paciente reenvía el correo del laboratorio/EPS a esa dirección.
3. La app se conecta por IMAP (`imaplib`, librería estándar de Python) a esa bandeja —
   automáticamente cada `EMAIL_POLL_MINUTES` (por defecto 15) vía un job en segundo plano
   (`APScheduler`), y también bajo demanda con el botón "Ya reenvié — revisar ahora" en
   `/correo`.
4. Solo se procesan correos cuyo remitente coincida **exactamente** con el correo registrado del
   paciente (`Patient.email`, editable en `/correo`) — cualquier otro remitente (spam,
   publicidad) se ignora sin gastar una sola llamada a la IA.
5. Se extrae tanto el **cuerpo de texto** del correo (si tiene contenido médico útil — la propia
   IA descarta cuerpos irrelevantes tipo "ver adjunto" o firmas) como los **adjuntos** (PDF o
   foto), reutilizando el mismo motor de extracción de la Fase 1 (`ai_extract.py`).
6. **La confirmación humana sigue siendo obligatoria.** Nada se guarda como `HealthEvent` de
   una — cada candidato queda en la tabla `PendingEmailEvent` hasta que el paciente lo revisa y
   confirma (o lo descarta) en `/correo/{id}`, con la misma pantalla de revisión que ya se usaba
   para foto/PDF.
7. La contraseña real de la cuenta de Gmail nunca se usa ni se guarda: Gmail exige activar
   verificación en 2 pasos y generar una "contraseña de aplicación" específica para IMAP,
   revocable en cualquier momento sin afectar el acceso normal a la cuenta — es lo único que va
   en `GMAIL_APP_PASSWORD` dentro de `.env`.

**Por qué es solo MVP de un usuario por ahora:** el filtro por remitente (`Patient.email`) hace
las veces de "autenticación" mínima mientras no exista la Fase 4 real — funciona bien para un
solo paciente real (o unos pocos, cada uno con su correo distinto registrado), pero no reemplaza
aislamiento de datos ni autenticación real a nivel de sesión/cuenta. Antes de ofrecerle esto a
terceros no relacionados habría que completar la Fase 4 (autenticación real, aislamiento por
usuario en BD, cifrado, revisión de Ley 1581/habeas data) — ver esa sección arriba.

**Código relevante:** `backend/app/email_ingest.py` (conexión IMAP y extracción),
`backend/app/models.py::PendingEmailEvent` (candidatos pendientes),
`backend/app/routers/correo.py` (rutas `/correo`), job periódico registrado en `main.py` al
arrancar la app (solo si `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` están configurados en `.env`).

---

## Fase 5 — Integración con instituciones médicas (planeada)

- **Exportación/importación en formato FHIR real** (JSON conforme al estándar HL7 FHIR R4),
  para que una institución pueda enviar o recibir datos de forma estandarizada. Como
  `HealthEvent` ya está modelado por categoría FHIR, esto es principalmente un mapeo de
  campos, no un rediseño.
- **Trazabilidad y consentimiento**: quién cargó cada dato, cuándo, con qué nivel de
  verificación (autorreportado por el paciente vs. confirmado por un profesional/institución)
  — esto ya existe parcialmente en el campo `source` de cada evento (la Fase 1 ya distingue
  "Foto analizada con IA — confirmado por el paciente" como fuente).
- **Cumplimiento normativo**: dependiendo del país y de si se maneja información de terceros,
  esta fase implica revisar requisitos de protección de datos de salud (en Colombia, la Ley
  1581 de 2012 y normas de habeas data; si se maneja información de pacientes de EE.UU.,
  HIPAA). Esto se debe evaluar con asesoría legal antes de manejar datos de terceros o de
  integrarse con una institución — no es un tema puramente técnico.

---

## Consideraciones transversales (aplican desde la Fase 1 en adelante)

- **Privacidad**: documentos y fotos con datos de salud se procesan con el mismo cuidado ya
  aplicado al correo — nada se comparte ni se guarda de terceros sin confirmación del usuario.
  La imagen subida en la Fase 1 se envía a la API de Claude para su análisis y no se guarda en
  el servidor más allá de la sesión de confirmación.
- **Llave de API**: el acceso a la API de Claude (Fases 1 y 3) se maneja como variable de
  entorno (`.env`, ya en `.gitignore`), nunca en el código ni en el repositorio. Implementado
  en `app/config.py` desde la Fase 1.
- **Pruebas continuas**: cada fase nueva llega con sus propias pruebas automáticas antes de
  darse por terminada. La Fase 1 agregó pruebas que simulan la extracción de la IA
  (`monkeypatch`) para no depender de la red ni de una llave real al correr `pytest`.
- **La IA no diagnostica**: en la Fase 3, el prompt está diseñado para describir y sugerir,
  nunca para emitir un diagnóstico o una prescripción. El prompt de la Fase 1 ya sigue el mismo
  principio: solo transcribe lo que ve, nunca interpreta ni completa valores no visibles.

## Datos deportivos (pendiente, fuera de las fases numeradas)

Los datos deportivos mencionados en el perfil del usuario (gimnasio, ciclismo, atletismo) no
estaban en el correo y se pueden agregar sin cambiar la arquitectura: manualmente vía
`/eventos/nuevo`, por foto vía `/importar` (Fase 1, ya funcional para cualquier tipo de
documento), o como extensión futura (categorías FHIR adicionales tipo `Observation` con
categoría "activity", o integración con un reloj deportivo/app de entrenamiento).
