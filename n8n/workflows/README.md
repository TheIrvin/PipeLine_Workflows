Cada workflow se importa desactivado. Activa reposición, watcher de aprobación, planificador V3 y producción cuando los servicios de API estén healthy. No hacen llamadas externas.
- `planner-worker.json`: planifica los trabajos aprobados y crea los cuatro artefactos locales V3 cada minuto.
- `production-worker.json`: corre medios mock, TTS, montaje, subtítulos, metadata y QA cada minuto; procesa un job a la vez.
