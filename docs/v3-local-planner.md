# V3 — Planificador local

V3 transforma cada trabajo `IDEA_APPROVED` en cuatro documentos locales:

- `plan.json`: concepto, enfoque, hook, resultado, CTA, creación, habilidad, debilidad y estadísticas.
- `script.json`: texto visible/TTS en español, duración y pronunciaciones especiales.
- `scenes.json`: escenas con orden, duración, tipo, descripción, requisito y estado.
- `media_prompts.json`: grupos PROMPT_A/B/C con continuidad visual 9:16.

El planificador redacta cada idea con Ollama en local (Qwen 3 4B). Adapta el patrón narrativo al tema —por ejemplo explicación, hipótesis, comparación, misterio o consecuencia— para evitar guiones con la misma estructura. No requiere Google Cloud ni envía los guiones a un proveedor externo. Cada paquete se guarda en `data/jobs/CONTENT-ID/`. Valida guion, CTA, duración, prompts y consistencia de escenas antes de avanzar el trabajo por `SCRIPT_READY` a `MEDIA_QUEUED`.

La API expone `POST /api/planner/process` y `GET /api/jobs/CONTENT-ID`. El workflow `n8n/workflows/planner-worker.json` solicita el procesamiento cada minuto. Los documentos se regeneran de forma idempotente si se vuelve a pedir el mismo trabajo.

Para generar un paquete local desde Ubuntu:

```bash
cd ~/PipeLine_Workflows
python3 -m services.idea_bank.cli plan CONTENT-000001
```

Los jobs existen solamente después de aprobar una idea. La aprobación sigue siendo manual en el panel; una idea no se aprueba automáticamente.
