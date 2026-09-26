# Worker de producción

La API procesa trabajos por checkpoints y conserva el estado en SQLite. `MEDIA_PROVIDER=manual-inbox` es el valor predeterminado: las escenas y sus prompts se preparan localmente; cuando el usuario deja un MP4 completo como `video_completo.mp4` en la bandeja de Descargas (o los medios por escena como alternativa), el worker lo valida y ajusta su duración a la narración antes de subtítulos, metadata y QA. Se puede usar `MEDIA_PROVIDER=mock` para generar PPM de demostración.

Los medios de video admitidos son MP4, MOV, WebM y MKV; las imágenes admitidas son PNG, JPG, JPEG, WebP y PPM. El video completo se normaliza a vertical 9:16, se ajusta a la duración real del WAV y recibe un zoom/paneo discreto. La alternativa de clips separados los ajusta a la duración de cada escena.
