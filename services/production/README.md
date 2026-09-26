# Worker local de producción

La API procesa un trabajo cada vez en memoria y conserva el checkpoint en SQLite. Provider media es mock; TTS usa espeak-ng con el diccionario de pronunciación editable en pronunciation_dictionary.json. Puedes escoger TTS_VOICE y TTS_SPEED desde variables de entorno.

El audio usa texto de voz del guion; los subtítulos salen del texto visible aprobado y no del resultado de ASR. FFmpeg valida el master y genera el export vertical H.264/AAC.

La API queda publicada solo en loopback mediante Compose. /healthz informa disponibilidad; /api/production/process procesa jobs pendientes; /api/jobs/CONTENT-ID/resume reanuda una tarea; /api/jobs/CONTENT-ID/publish-dry-run genera una simulación. El último endpoint nunca publica en redes.
