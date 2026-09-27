# V4–V9 — Producción, subtítulos, QA y publicación segura

## Modo local por defecto

- V4 usa `ManualMediaProvider` por defecto: espera imágenes o clips generados por el usuario en la bandeja de entrada del trabajo, los valida con ffprobe y los importa sin borrar los originales. `MEDIA_PROVIDER=mock` activa imágenes PPM solo para demostraciones locales.
- V5 usa Qwen3-TTS 0.6B local para clonar la voz de referencia sin clave API, aplica el diccionario configurable pronunciation_dictionary.json y FFmpeg para el master H.264/AAC vertical 9:16.
- V6 conserva el texto aprobado y delega la sincronización y el render al backend existente del Mini Editor de Subtítulos, integrado como submódulo y servicio interno Docker. El sidecar SRT conserva los bloques y tiempos para QA.
- V7 genera JSON para TikTok, Facebook, Instagram y YouTube Shorts; verifica archivos, reproducción, duración, proporción, códecs y metadatos, y añade el contenido al buffer local. Mínimo 7 y objetivo 14. No publica automáticamente al alcanzar el mínimo.
- V8 incluye adaptadores por plataforma en dry-run. No envían publicaciones reales ni guardan credenciales.
- V9 incluye checkpoints, reintentos, logs JSONL y prueba end-to-end. FFmpeg, espeak-ng y la API del worker tienen health checks.

## Archivos

data/jobs/CONTENT-ID/: plan, guion, escenas y prompts.
data/assets/CONTENT-ID/videos/ y images/: copias de medios validados e importados desde `videos/subir/CONTENT-ID/`.
data/assets/CONTENT-ID/audio/: WAV de narración.
data/assets/CONTENT-ID/masters/: master sin subtítulos, master final y reporte QA.
data/assets/CONTENT-ID/subtitles/: subtítulos SRT.
data/assets/CONTENT-ID/metadata/: metadata de plataformas y dry-runs.

Los originales válidos no se borran ni sobrescriben durante una reanudación. Los checkpoints se guardan en SQLite y los eventos en data/logs/pipeline.jsonl.


## Entrega manual de prompts y video unido

Al aprobar una idea, el worker crea `videos/subir/CONTENT-ID/` dentro del repositorio, con las carpetas `imagenes` y `animar_imagenes`. Los prompts y archivos de trabajo quedan separados por contenido. Puedes entregar los medios de cualquiera de estas formas:

- Un MP4 editado/unido por ti, llamado `video_completo.mp4` directamente en `videos/subir/CONTENT-ID/`.
- Clips separados `clip_01.mp4`, `clip_02.mp4`, etc., dentro de `videos/subir/CONTENT-ID/animar_imagenes/` (también se aceptan en la raíz del trabajo).
- Medios con el nombre del ID de escena, si ya tienes una integración que los genera así.

Con clips separados, el worker respeta el orden y aplica a cada escena el tiempo objetivo del plan. Para elegir manualmente la duración y el ritmo de cada corte, une los clips en un editor y entrega `video_completo.mp4`.

El worker valida y copia los originales a `data/assets/CONTENT-ID/`, añade narración y subtítulos locales, ajusta el montaje vertical y ejecuta QA. No borra los archivos de `subir`, para permitir reintentos. Después de aprobar QA, copia el MP4 final con audio y subtítulos a `videos/terminado/CONTENT-ID.mp4`; el master de trabajo también permanece en `data/assets/CONTENT-ID/masters/`.

Para ver la carpeta en Windows desde Ubuntu/WSL, ejecuta `explorer.exe "$(wslpath -w "$PWD/videos")"` desde la raíz del repositorio. Si prefieres guardarla fuera del repo, configura `MEDIA_INBOX_HOST_PATH` en `.env` con una ruta absoluta de tu equipo; el contenido de medios no se sube a Git.

Los prompts no fijan duración. Genera cada imagen con su referencia de personaje real y usa la imagen numerada correspondiente para generar su clip. La guía completa está en `.agents/skills/pipeline-visual-media/`. Si el workflow de producción de n8n está activo, revisa las entregas periódicamente; también puedes llamar `POST /api/jobs/CONTENT-ID/resume`.

## Subtitulador local integrado

Compose inicia el servicio interno `subtitle-worker` junto al productor. No expone un puerto en Windows ni necesita que se abra el Mini Editor de escritorio. El pipeline envía el master y el guion aprobado a sus rutas `upload`, `manual-subtitles`, `export` y `download`; el backend detecta los tiempos de voz con faster-whisper en CPU y mantiene el texto exacto enviado. El vídeo exportado regresa al directorio local de assets.

La primera transcripción descarga el modelo Whisper base desde Hugging Face y lo conserva en `data/models`. Requiere Internet solo para esa descarga; las siguientes ejecuciones reutilizan el modelo. El servicio y los datos de proyectos quedan en `data/subtitle-worker`. No se necesitan Google Cloud ni las dependencias de traducción, porque el pipeline envía solo el texto español aprobado.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.


## Guion y voz clonada local

Ollama con Qwen 3 4B escribe el guion en local y escoge un patrón narrativo distinto según la idea. Qwen3-TTS 0.6B sintetiza en español en una segunda etapa local, sin clave API. Usa la referencia privada data/models/voice-reference/Audio_Ejemplo.mp3 y la transcripción exacta en Audio_Ejemplo.txt. Los modelos se descargan al primer uso y quedan en data/models/qwen3-tts-huggingface/. Ollama descarga su modelo de memoria al acabar de generar el guion para dejar RAM disponible para la síntesis.

La voz se clona usando audio y transcripción como entrada. Mantén ambos archivos privados; data/ está excluido de Git. El endpoint para rehacer un job READY con el guion y voz clonada, guardando una copia de la versión previa, es POST http://localhost:8091/api/jobs/CONTENT-000001/rebuild-narration.
