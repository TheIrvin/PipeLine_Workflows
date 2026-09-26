# Worker de producción

La API procesa trabajos por checkpoints y conserva el estado en SQLite. `MEDIA_PROVIDER=manual-inbox` es el valor predeterminado: las escenas y sus prompts se preparan localmente; cuando el usuario deja un MP4 completo como `video_completo.mp4` en la carpeta principal del trabajo en Descargas, el worker lo valida y continúa con voz local, subtítulos, metadata y QA. Los prompts están separados en las subcarpetas `imagenes` y `animar_imagenes`. Se puede usar `MEDIA_PROVIDER=mock` para generar PPM de demostración.

Los medios de video admitidos son MP4, MOV, WebM y MKV; las imágenes admitidas son PNG, JPG, JPEG, WebP y PPM. El video unido se normaliza a vertical 9:16 y se ajusta a la duración real del WAV con un zoom/paneo discreto.
