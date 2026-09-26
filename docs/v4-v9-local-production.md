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


## Entrega manual de imágenes y clips

Al aprobar una idea, el paquete de prompts queda en `data/jobs/CONTENT-ID/media_prompts.md` y el JSON editable en `media_prompts.json`. Abre el Markdown: contiene por escena el contexto de narración, un prompt para crear la imagen de referencia y otro para animarla. El prompt de video sugiere clips de unos 8 segundos; el montaje ajusta cada clip a la duración de su escena, recortando el exceso o congelando el último fotograma si queda corto.

Guarda los videos en `data/assets/CONTENT-ID/inbox/` con el nombre exacto `CONTENT-ID-SCENE-01.mp4`, `CONTENT-ID-SCENE-02.mp4`, etc. Se admiten MP4, MOV, WebM y MKV. Si una escena no se puede animar, usa el mismo nombre terminado en `.png`, `.jpg`, `.jpeg` o `.webp`; basta con entregar un medio por escena. El worker no inicia audio/montaje hasta completar todas las escenas. Si el workflow de producción de n8n está activo, revisa la bandeja cada minuto y reanuda el trabajo cuando está completa. También puedes llamar `POST /api/jobs/CONTENT-ID/resume`.

Desde Windows, la carpeta está en `\\wsl.localhost\Ubuntu\home\irvin\PipeLine_Workflows\data\assets\CONTENT-ID\inbox`. No se requiere configurar Gemini, ChatGPT ni credenciales de Google en el pipeline. Para reducir fallos de copia, espera a que termine cada descarga antes de dejar el archivo en la bandeja.

## Subtitulador local integrado

Compose inicia el servicio interno `subtitle-worker` junto al productor. No expone un puerto en Windows ni necesita que se abra el Mini Editor de escritorio. El pipeline envía el master y el guion aprobado a sus rutas `upload`, `manual-subtitles`, `export` y `download`; el backend detecta los tiempos de voz con faster-whisper en CPU y mantiene el texto exacto enviado. El vídeo exportado regresa al directorio local de assets.

La primera transcripción descarga el modelo Whisper base desde Hugging Face y lo conserva en `data/models`. Requiere Internet solo para esa descarga; las siguientes ejecuciones reutilizan el modelo. El servicio y los datos de proyectos quedan en `data/subtitle-worker`. No se necesitan Google Cloud ni las dependencias de traducción, porque el pipeline envía solo el texto español aprobado.

## Publicación

POST /api/jobs/CONTENT-ID/publish-dry-run genera una simulación para las cuatro plataformas. La publicación real requiere configuración y autorización explícita en cada plataforma. No se necesita Google Cloud.


## Guion y voz clonada local

Ollama con Qwen 3 4B escribe el guion en local y escoge un patrón narrativo distinto según la idea. Qwen3-TTS 0.6B sintetiza en español en una segunda etapa local, sin clave API. Usa la referencia privada data/models/voice-reference/Audio_Ejemplo.mp3 y la transcripción exacta en Audio_Ejemplo.txt. Los modelos se descargan al primer uso y quedan en data/models/qwen3-tts-huggingface/. Ollama descarga su modelo de memoria al acabar de generar el guion para dejar RAM disponible para la síntesis.

La voz se clona usando audio y transcripción como entrada. Mantén ambos archivos privados; data/ está excluido de Git. El endpoint para rehacer un job READY con el guion y voz clonada, guardando una copia de la versión previa, es POST http://localhost:8091/api/jobs/CONTENT-000001/rebuild-narration.
