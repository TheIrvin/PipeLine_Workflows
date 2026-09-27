# Worker de producción

El worker procesa los medios que el usuario entrega en `videos/subir/CONTENT-ID/`. Acepta un MP4 completo llamado `video_completo.mp4`, clips numerados `animar_imagenes/clip_XX.mp4`, o archivos identificados por el ID de escena. Si existe el MP4 completo, tiene prioridad. Los originales se conservan para reintentar.

Después de añadir la voz aprobada, montar el video vertical, sincronizar subtítulos y pasar QA, el worker copia el resultado final a `videos/terminado/CONTENT-ID.mp4`. Los masters, manifiestos y metadatos de producción permanecen en `data/assets/CONTENT-ID/`.

`MEDIA_PROVIDER=manual-inbox` es el modo predeterminado. `MEDIA_PROVIDER=mock` crea medios PPM locales para demostraciones. La voz predeterminada usa Qwen3-TTS local y requiere una muestra con su transcripción exacta. La guía de instalación y operación está en el [README principal](../../README.md).

El montaje admite MP4, MOV, WebM y MKV para clips y PNG, JPG, JPEG, WebP y PPM para imágenes. Los clips separados se ordenan por escena y se ajustan a la duración objetivo de cada escena; para ajustar manualmente el ritmo, entrega un `video_completo.mp4` ya unido.
