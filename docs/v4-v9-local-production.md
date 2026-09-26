# V4–V9 — Producción, subtítulos, QA y publicación segura

## Modo local por defecto

- V4 usa MockMediaProvider: crea imágenes PPM deterministas y un manifiesto, sin Gemini, cuotas ni llamadas de red.
- V5 usa espeak-ng sin conexión para TTS, aplica el diccionario configurable pronunciation_dictionary.json y FFmpeg para el master H.264/AAC vertical 9:16.
- V6 conserva el texto aprobado y crea subtítulos temporizados localmente. Se inspeccionó el backend existente de Mini Editor Subtítulos; no se modificó. El adaptador opcional ExistingSubtitleBackendAdapter utiliza sus rutas upload, manual-subtitles, export y download si se configura SUBTITLE_WORKER_URL.
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

## Adaptador del subtitulador existente

Para usar el backend FastAPI del Mini Editor en Windows:
1. Inicia el backend del Mini Editor.
2. Configura SUBTITLE_WORKER_URL=http://host.docker.internal:8000 en production-worker.
3. Configura SUBTITLE_EXPORT_DIR con una carpeta de Windows accesible para ese proceso.
4. Reinicia el contenedor y verifica /api/health.

El worker descarga el MP4 final por HTTP y lo copia a los assets de Ubuntu. Whisper puede tardar la primera vez en descargar/cargar su modelo. Si requiere login, permisos o una acción manual, resuélvelo en la UI original. El subtitulador local exacto sigue disponible sin esa API.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.
