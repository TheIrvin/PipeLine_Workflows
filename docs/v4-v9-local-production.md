# V4–V9 — Producción, subtítulos, QA y publicación segura

## Modo local por defecto

- V4 usa MockMediaProvider: crea imágenes PPM deterministas y un manifiesto, sin Gemini, cuotas ni llamadas de red.
- V5 usa espeak-ng sin conexión para TTS, aplica el diccionario configurable pronunciation_dictionary.json y FFmpeg para el master H.264/AAC vertical 9:16.
- V6 conserva el texto aprobado y delega la sincronización y el render al backend existente del Mini Editor de Subtítulos, integrado como submódulo y servicio interno Docker. El sidecar SRT conserva los bloques y tiempos para QA.
- V7 genera JSON para TikTok, Facebook, Instagram y YouTube Shorts; verifica archivos, reproducción, duración, proporción, códecs y metadatos, y añade el contenido al buffer local. Mínimo 7 y objetivo 14. No publica automáticamente al alcanzar el mínimo.
- V8 incluye adaptadores por plataforma en dry-run. No envían publicaciones reales ni guardan credenciales.
- V9 incluye checkpoints, reintentos, logs JSONL y prueba end-to-end. FFmpeg, espeak-ng y la API del worker tienen health checks.

## Archivos

data/jobs/CONTENT-ID/: plan, guion, escenas y prompts.
data/assets/CONTENT-ID/images/: imágenes mock originales.
data/assets/CONTENT-ID/audio/: WAV de narración.
data/assets/CONTENT-ID/masters/: master sin subtítulos, master final y reporte QA.
data/assets/CONTENT-ID/subtitles/: subtítulos SRT.
data/assets/CONTENT-ID/metadata/: metadata de plataformas y dry-runs.

Los originales válidos no se borran ni sobrescriben durante una reanudación. Los checkpoints se guardan en SQLite y los eventos en data/logs/pipeline.jsonl.

## Subtitulador local integrado

Compose inicia el servicio interno `subtitle-worker` junto al productor. No expone un puerto en Windows ni necesita que se abra el Mini Editor de escritorio. El pipeline envía el master y el guion aprobado a sus rutas `upload`, `manual-subtitles`, `export` y `download`; el backend detecta los tiempos de voz con faster-whisper en CPU y mantiene el texto exacto enviado. El vídeo exportado regresa al directorio local de assets.

La primera transcripción descarga el modelo Whisper base desde Hugging Face y lo conserva en `data/models`. Requiere Internet solo para esa descarga; las siguientes ejecuciones reutilizan el modelo. El servicio y los datos de proyectos quedan en `data/subtitle-worker`. No se necesitan Google Cloud ni las dependencias de traducción, porque el pipeline envía solo el texto español aprobado.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.
