# V2 — Banco local de ideas y aprobación

## Diseño local

- Interfaz `TextAIProvider` y `MockTextAIProvider`, sin llamadas de red ni claves.
- SQLite en `data/ideas/ideas.db`.
- Panel local en `http://localhost:8090` para generar ideas y aprobar/rechazar.
- La aprobación humana marca `APROBADA`; n8n vigila el estado, crea un único job `CONTENT-XXXXXX` con `IDEA_APPROVED` y avanza la idea a `EN_PRODUCCION`.
- Workflow de reposición mock revisa el umbral de 30 y genera un lote de hasta 30 cada hora.
- Los endpoints locales solo se publican en loopback. No se necesita Google Cloud, OAuth, tarjeta ni credenciales externas.

## Uso del mock desde Ubuntu

```bash
cd ~/PipeLine_Workflows
python3 -m services.idea_bank.cli generate --count 30
python3 -m services.idea_bank.cli list
python3 -m services.idea_bank.cli approve IDEA-000001
python3 -m services.idea_bank.cli reject IDEA-000002
python3 -m unittest discover -s tests -v
```

La API del contenedor implementa además `/api/ideas`, `/api/ideas/replenish`, `/api/ideas/{id}/approve`, `/api/ideas/{id}/reject` y `/api/approvals/process`.

## Workflows

Importa y activa:

- `n8n/workflows/idea-replenisher.json`: comprueba el umbral cada hora.
- `n8n/workflows/idea-approval-watcher.json`: procesa aprobaciones cada minuto.

Ambos usan el nombre interno de servicio `idea-bank-api`, disponible dentro de la red Docker Compose.

## Pruebas

`python3 -m unittest discover -s tests -v` cubre generación estructurada, deduplicación incluso con tildes y signos, estados, rechazo, creación idempotente de jobs y aprobación desconocida.
