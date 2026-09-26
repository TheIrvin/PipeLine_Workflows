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
data/assets/CONTENT-ID/videos/ y images/: medios validados e importados desde la carpeta de Descargas.
data/assets/CONTENT-ID/audio/: WAV de narración.
data/assets/CONTENT-ID/masters/: master sin subtítulos, master final y reporte QA.
data/assets/CONTENT-ID/subtitles/: subtítulos SRT.
data/assets/CONTENT-ID/metadata/: metadata de plataformas y dry-runs.

Los originales válidos no se borran ni sobrescriben durante una reanudación. Los checkpoints se guardan en SQLite y los eventos en data/logs/pipeline.jsonl.


## Entrega manual de prompts y video unido

Al aprobar una idea, se crea `C:\Users\irvin\Downloads\Pipeline_Workflows\ManualMedia\CONTENT-ID\` con dos subcarpetas: `imagenes` y `animar_imagenes`. En cada una encontrarás prompts numerados que se corresponden: `imagenes/prompt_01.txt` crea `imagen_01.png`; `animar_imagenes/prompt_01.txt` anima esa imagen y sugiere guardar `clip_01.mp4`. Repite por cada número. Los prompts no fijan una duración.

Genera las imágenes y clips manualmente, une los clips en tu editor y guarda el único MP4 unido como `video_completo.mp4` directamente en la carpeta `CONTENT-ID`, junto a `LEEME.txt`. No lo pongas dentro de una tercera carpeta. El worker valida ese MP4 y continúa con la voz local, el montaje vertical, subtítulos, metadata y QA. El video se ajusta al largo real de la narración sintetizada; el texto de subtítulos se conserva y sus tiempos se detectan desde el audio.

La carpeta de Descargas se monta en Docker mediante `MEDIA_INBOX_HOST_PATH`; los medios importados se guardan en `data/assets/CONTENT-ID/videos/`. Los originales de Descargas se conservan. Si el workflow de producción de n8n está activo, revisa el archivo cada minuto. También puedes llamar `POST /api/jobs/CONTENT-ID/resume`.

## Subtitulador local integrado

Compose inicia el servicio interno `subtitle-worker` junto al productor. No expone un puerto en Windows ni necesita que se abra el Mini Editor de escritorio. El pipeline envía el master y el guion aprobado a sus rutas `upload`, `manual-subtitles`, `export` y `download`; el backend detecta los tiempos de voz con faster-whisper en CPU y mantiene el texto exacto enviado. El vídeo exportado regresa al directorio local de assets.

La primera transcripción descarga el modelo Whisper base desde Hugging Face y lo conserva en `data/models`. Requiere Internet solo para esa descarga; las siguientes ejecuciones reutilizan el modelo. El servicio y los datos de proyectos quedan en `data/subtitle-worker`. No se necesitan Google Cloud ni las dependencias de traducción, porque el pipeline envía solo el texto español aprobado.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.


## Guion y voz clonada local

Ollama con Qwen 3 4B escribe el guion en local y escoge un patrón narrativo distinto según la idea. Qwen3-TTS 0.6B sintetiza en español en una segunda etapa local, sin clave API. Usa la referencia privada data/models/voice-reference/Audio_Ejemplo.mp3 y la transcripción exacta en Audio_Ejemplo.txt. Los modelos se descargan al primer uso y quedan en data/models/qwen3-tts-huggingface/. Ollama descarga su modelo de memoria al acabar de generar el guion para dejar RAM disponible para la síntesis.

La voz se clona usando audio y transcripción como entrada. Mantén ambos archivos privados; data/ está excluido de Git. El endpoint para rehacer un job READY con el guion y voz clonada, guardando una copia de la versión previa, es POST http://localhost:8091/api/jobs/CONTENT-000001/rebuild-narration.
