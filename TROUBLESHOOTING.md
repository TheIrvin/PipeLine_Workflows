# Solución de problemas

- Docker: inicia Docker Desktop y comprueba docker compose ps.
- API del banco: docker compose logs --tail=100 idea-bank-api.
- Worker: docker compose logs --tail=150 production-worker.
- FFmpeg: docker exec pipeline-production-worker ffmpeg -version.
- TTS: docker exec pipeline-production-worker espeak-ng --version.
- Job RETRY_PENDING: corrige el problema indicado en data/logs/pipeline.jsonl y llama al endpoint resume.
- Subtitulador externo: confirma el backend en Windows y la URL accesible desde el contenedor; el modo local no depende de él.
- Espacio: assets de video ocupan disco; archiva manualmente solo trabajos que ya no necesites.
- Publicación: el modo actual es dry-run, no se envía contenido a redes.
