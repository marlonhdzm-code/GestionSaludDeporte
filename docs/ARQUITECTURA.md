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

**Estado:** app funcional, precargada con tus 58 eventos reales, 5/5 pruebas pasando, repo git
local inicializado.

---

## Fase 1 — Ingesta desde correo, documento o foto (siguiente, pedida por el usuario)

**Objetivo:** que suministres un correo, un PDF o la foto de un examen, y la app extraiga los
datos e incorpore el evento automáticamente, sin transcripción manual.

**Flujo:**

1. **Carga** — endpoint `/importar`: subir un PDF, una imagen (foto de un examen), o pegar el
   texto de un correo.
2. **Extracción de texto** — PDF digital: texto directo (`pdfplumber`); foto o PDF escaneado:
   OCR (`pytesseract` u otro motor).
3. **Estructuración con IA** — el texto crudo se envía a un modelo de lenguaje (API de Claude)
   con un prompt que le pide identificar categoría FHIR, fecha, tipo de evento, valor, rango de
   referencia e institución, devuelto en JSON conforme a `schemas.HealthEventCreate`.
4. **Confirmación humana obligatoria** — el resultado se muestra en un formulario prellenado
   junto al documento original; nada se guarda en la base de datos sin que el usuario lo
   confirme o corrija. Esto es innegociable: un dato de salud mal transcrito es peor que no
   tenerlo.

**Construido con:** `pdfplumber`, `pytesseract`, API de Claude (Anthropic), nuevo endpoint
`/importar` en `routers/`.

**Riesgo a vigilar:** calidad de OCR en fotos de mala calidad — se mitiga mostrando siempre la
imagen original junto al formulario de confirmación, nunca guardando a ciegas.

---

## Fase 2 — Tendencias en el tiempo (planeada, pedida por el usuario)

**Objetivo:** ver la evolución de cualquier prueba (colesterol, glucosa, TSH...) como una
gráfica en el tiempo, no como filas sueltas en una tabla.

**Qué incluye:**

- Vista "Tendencias": elegir un analito (por título de `HealthEvent`) y graficar su serie
  temporal usando `event_date_sort`.
- El `reference_range` de cada evento se dibuja como banda de fondo, para detectar de un
  vistazo cuándo un valor cayó fuera de rango.
- Filtro por categoría FHIR y por rango de fechas.
- Caso ya visible en los datos actuales: colesterol total bajando de 265 a 137 mg/dL entre
  jun-2024 y ago-2026.

**Construido con:** Chart.js (vía CDN, sin backend adicional — consume `/api/events` que ya
existe).

---

## Fase 3 — Resumen con IA: interpretación, recomendaciones y alertas (planeada, pedida por el usuario)

**Objetivo:** un botón que le pide a la IA leer todo el historial del paciente y devolver un
resumen en lenguaje claro — tendencias relevantes, valores a vigilar, preguntas sugeridas para
el médico — siempre dejando explícito que no reemplaza una evaluación profesional.

**Qué incluye:**

- Botón "Generar resumen" → envía el historial (o un rango de fechas) a la API de Claude con
  un prompt clínico diseñado para **describir y correlacionar, nunca diagnosticar ni
  prescribir**.
- Detecta valores fuera de `reference_range` y tendencias relevantes (por ejemplo, respuesta a
  un cambio de medicación, visible cruzando `Observation` con `MedicationStatement`).
- Sugiere preguntas concretas para la siguiente cita médica.
- Cada resumen se guarda con fecha (tabla `AiSummary`, por definir) y se puede exportar a PDF.
- **Todo resumen generado abre con un aviso fijo, no opcional:** "Esto fue generado por
  inteligencia artificial, no soy médico y esto no reemplaza una evaluación profesional — te
  sugiero compartir este resumen con tu médico tratante."

**Construido con:** API de Claude, prompt clínico con guardrails explícitos, exportación a PDF
(reutilizando el patrón ya usado para el registro de salud en Word/Excel).

---

## Fase 4 — Multiusuario y despliegue en la nube (planeada)

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

---

## Fase 5 — Integración con instituciones médicas (planeada)

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

---

## Consideraciones transversales (aplican desde la Fase 1 en adelante)

- **Privacidad**: documentos y fotos con datos de salud se procesan con el mismo cuidado ya
  aplicado al correo — nada se comparte ni se guarda de terceros sin confirmación del usuario.
- **Llave de API**: el acceso a la API de Claude (Fases 1 y 3) se maneja como variable de
  entorno (`.env`, ya en `.gitignore`), nunca en el código ni en el repositorio.
- **Pruebas continuas**: cada fase nueva llega con sus propias pruebas automáticas antes de
  darse por terminada, igual que la Fase 0.
- **La IA no diagnostica**: en la Fase 3, el prompt está diseñado para describir y sugerir,
  nunca para emitir un diagnóstico o una prescripción.

## Datos deportivos (pendiente, fuera de las fases numeradas)

Los datos deportivos mencionados en el perfil del usuario (gimnasio, ciclismo, atletismo) no
estaban en el correo y se pueden agregar sin cambiar la arquitectura: manualmente vía
`/eventos/nuevo`, o como extensión futura (categorías FHIR adicionales tipo `Observation` con
categoría "activity", o integración con un reloj deportivo/app de entrenamiento).
