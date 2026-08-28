# Arquitectura y hoja de ruta

## Fase 0 (esta versión) — App personal en tu computador

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

## Fase 1 — Multiusuario y despliegue en la nube

Cuando el objetivo pase de "mi app personal" a "una app que otras personas puedan usar":

1. **Autenticación de usuarios** (login, sesiones) — cada usuario ve solo sus propios
   pacientes/eventos. FastAPI tiene soporte maduro para esto (OAuth2/JWT).
2. **Migrar la base de datos a Postgres** (Supabase, Railway, RDS, etc.) — un solo cambio de
   variable de entorno, sin reescribir el modelo de datos.
3. **Migraciones de esquema con Alembic**, en vez de `Base.metadata.create_all()` (que solo
   sirve para desarrollo local).
4. **Despliegue** en un servicio como Railway, Render o Fly.io — el mismo código FastAPI corre
   sin cambios, solo se agrega un `Dockerfile`.
5. **Frontend dedicado** (opcional, si la interfaz Jinja2 se queda corta): un frontend en React
   o similar que consuma la API `/api/...` ya existente, sin tocar el backend.

## Fase 2 — Integración con instituciones médicas

- **Exportación/importación en formato FHIR real** (JSON conforme al estándar HL7 FHIR R4),
  para que una institución pueda enviar o recibir datos de forma estandarizada. Como
  `HealthEvent` ya está modelado por categoría FHIR, esto es principalmente un mapeo de
  campos, no un rediseño.
- **Trazabilidad y consentimiento**: quién cargó cada dato, cuándo, con qué nivel de
  verificación (autorreportado por el paciente vs. confirmado por un profesional/institución)
  — esto ya existe parcialmente en el campo `source` de cada evento.
- **Cumplimiento normativo**: dependiendo del país y de si se maneja información de terceros,
  esta fase implica revisar requisitos de protección de datos de salud (en Colombia, la Ley
  1581 de 2012 y normas de habeas data; si se maneja información de pacientes de EE.UU.,
  HIPAA). Esto se debe evaluar con asesoría legal antes de manejar datos de terceros o de
  integrarse con una institución — no es un tema puramente técnico.

## Fase 3 — Motor de IA: correlación, alertas y planes de salud

Una vez haya suficientes datos reales cargados (la razón por la que se decidió posponer esta
fase):

- **Correlación de tendencias**: por ejemplo, cruzar la serie temporal de `Observation`
  (colesterol, glucosa, TSH...) con `MedicationStatement` (cuándo empezó cada medicamento) para
  detectar respuesta a tratamiento — ya se ve un caso real en los datos cargados: el colesterol
  total bajó de 265 a 137 mg/dL después de iniciar tratamiento con estatina.
- **Alertas basadas en rangos de referencia**: cada `Observation` ya guarda su
  `reference_range`; un motor de reglas simple (antes de pensar en un modelo de IA más
  complejo) puede marcar valores fuera de rango y avisar.
- **Planes de salud personalizados**: combinar el historial médico con las métricas
  deportivas (fase de datos deportivos, ver más abajo) para sugerir ajustes — por ejemplo,
  relacionar la carga de entrenamiento con marcadores cardiovasculares.
- La arquitectura actual ya deja esto preparado: al ser todo `HealthEvent` con la misma forma,
  un servicio de IA puede leer directamente de `/api/events?patient_id=...` sin necesitar
  acceso especial a la base de datos.

## Datos deportivos (pendiente)

Este proyecto (fase 0) solo carga datos de salud extraídos del correo. Los datos deportivos
mencionados en tu perfil (gimnasio, ciclismo, atletismo) no estaban en el correo y se pueden
agregar de dos formas, sin cambiar la arquitectura:

1. Manualmente, vía el formulario `/eventos/nuevo`, usando categorías FHIR ya existentes
   (`Observation` sirve para métricas cuantitativas: distancia, frecuencia cardíaca, peso).
2. Como una extensión futura: una tabla `SportSession` o categorías FHIR adicionales
   (`Observation` con categoría "vital-signs" o "activity") si se conecta con datos de un reloj
   deportivo o app de entrenamiento.
