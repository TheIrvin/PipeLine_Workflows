# Worker de producción

La API procesa trabajos por checkpoints y conserva el estado en SQLite. `MEDIA_PROVIDER=manual-inbox` es el valor predeterminado: las escenas y sus prompts se preparan localmente; cuando el usuario deja todos los clips/imágenes requeridos en `data/assets/CONTENT-ID/inbox/`, el worker los valida y sigue con TTS, ensamblado, subtítulos, metadata y QA. Se puede usar `MEDIA_PROVIDER=mock` para generar PPM de demostración.

Los medios de video admitidos son MP4, MOV, WebM y MKV; las imágenes admitidas son PNG, JPG, JPEG, WebP y PPM. Los clips se normalizan a vertical 9:16 y se ajustan a la duración de escena.
