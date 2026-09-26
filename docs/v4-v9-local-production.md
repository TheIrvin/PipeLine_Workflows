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
data/assets/CONTENT-ID/inbox/: medios entregados manualmente, con un archivo por escena.
data/assets/CONTENT-ID/videos/ y images/: medios validados e importados. Los clips tienen prioridad; una imagen fija es alternativa.
data/assets/CONTENT-ID/audio/: WAV de narración.
data/assets/CONTENT-ID/masters/: master sin subtítulos, master final y reporte QA.
data/assets/CONTENT-ID/subtitles/: subtítulos SRT.
data/assets/CONTENT-ID/metadata/: metadata de plataformas y dry-runs.

Los originales válidos no se borran ni sobrescriben durante una reanudación. Los checkpoints se guardan en SQLite y los eventos en data/logs/pipeline.jsonl.


## Entrega manual de medios

Al aprobar una idea, se crea en Descargas `Pipeline_Workflows/ManualMedia/CONTENT-ID/`. Allí quedan `media_prompts.md` y la carpeta `inbox/`. El Markdown tiene un prompt para un video completo y, como alternativa, un prompt de imagen y otro de animación para cada escena.

La opción recomendada es copiar un único video a `Downloads/Pipeline_Workflows/ManualMedia/CONTENT-ID/inbox/video_completo.mp4`. También se acepta el alias `full_video.mp4`. Si prefieres entregar escenas separadas, usa los nombres exactos del Markdown; puede ser un MP4 por escena o una imagen PNG/JPG/JPEG/WebP para una escena sin animación. Se admiten videos MP4, MOV, WebM y MKV.

El video completo se recorta a vertical 9:16, recibe un zoom/paneo leve y se ajusta a la duración real de la narración sintetizada: se recorta si sobra video o se congela el último fotograma si falta. No se asignan duraciones fijas de 12 segundos por escena. Por ejemplo, si el primer bloque narrado dura 8 segundos y el siguiente 4, el video continuo sigue bajo la voz de 8+4 segundos, y los subtítulos se sincronizan contra el audio. Para que los cambios visuales coincidan con cambios concretos del guion, el video completo debe traer esos momentos en ese orden; el worker no puede inferir por sí solo el significado de cada fotograma.

Desde Windows, la carpeta queda en `C:\Users\irvin\Downloads\Pipeline_Workflows\ManualMedia\CONTENT-ID\inbox`; los prompts están al lado, en `media_prompts.md`. La ruta se configura con `MEDIA_INBOX_HOST_PATH` en `.env`. El video validado se copia al proyecto en `data/assets/CONTENT-ID/videos/`; el original de Descargas se conserva. Si el workflow de producción de n8n está activo, revisa la bandeja cada minuto y reanuda el trabajo; también puedes llamar `POST /api/jobs/CONTENT-ID/resume`.

## Subtitulador local integrado

Compose inicia el servicio interno `subtitle-worker` junto al productor. No expone un puerto en Windows ni necesita que se abra el Mini Editor de escritorio. El pipeline envía el master y el guion aprobado a sus rutas `upload`, `manual-subtitles`, `export` y `download`; el backend detecta los tiempos de voz con faster-whisper en CPU y mantiene el texto exacto enviado. El vídeo exportado regresa al directorio local de assets.

La primera transcripción descarga el modelo Whisper base desde Hugging Face y lo conserva en `data/models`. Requiere Internet solo para esa descarga; las siguientes ejecuciones reutilizan el modelo. El servicio y los datos de proyectos quedan en `data/subtitle-worker`. No se necesitan Google Cloud ni las dependencias de traducción, porque el pipeline envía solo el texto español aprobado.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.


## Guion y voz clonada local

Ollama con Qwen 3 4B escribe el guion en local y escoge un patrón narrativo distinto según la idea. Qwen3-TTS 0.6B sintetiza en español en una segunda etapa local, sin clave API. Usa la referencia privada data/models/voice-reference/Audio_Ejemplo.mp3 y la transcripción exacta en Audio_Ejemplo.txt. Los modelos se descargan al primer uso y quedan en data/models/qwen3-tts-huggingface/. Ollama descarga su modelo de memoria al acabar de generar el guion para dejar RAM disponible para la síntesis.

La voz se clona usando audio y transcripción como entrada. Mantén ambos archivos privados; data/ está excluido de Git. El endpoint para rehacer un job READY con el guion y voz clonada, guardando una copia de la versión previa, es POST http://localhost:8091/api/jobs/CONTENT-000001/rebuild-narration.
