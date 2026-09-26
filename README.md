# Pipeline automatizado de contenido

Base local del pipeline descrito en los prompts. n8n, el banco de ideas y el worker de producción corren en Docker Desktop; SQLite y los assets permanecen en Ubuntu WSL.

## Requisitos

- WSL2 con Ubuntu.
- Docker Desktop iniciado y la integración WSL de Ubuntu activa.
- Docker Compose v2 disponible (`docker compose version`).

## Rutas

- WSL: `/home/irvin/PipeLine_Workflows`
- Windows: `\\wsl.localhost\Ubuntu\home\irvin\PipeLine_Workflows`

Mantén el proyecto en el filesystem de Ubuntu (no en `/mnt/c`) para evitar problemas de rendimiento y permisos en los volúmenes.

## Iniciar y detener

Desde Ubuntu:

```bash
cd ~/PipeLine_Workflows
docker compose up -d
docker compose ps
```

- n8n: <http://localhost:5678>
- Banco y panel de ideas local: <http://localhost:8090>
- Worker local de producción: <http://localhost:8091/healthz>

```bash
docker compose stop       # detener sin borrar datos
docker compose start      # reanudar
docker compose logs -f n8n
docker compose logs -f idea-bank-api
```

Para actualizar n8n, cambia `N8N_VERSION` en `.env`, revisa primero las notas de versión, y ejecuta `docker compose pull && docker compose up -d`.

## Banco local de ideas

El panel permite generar el lote mock y aprobar o rechazar ideas. Una aprobación queda en estado `APROBADA`; el workflow importable de n8n la convierte en `EN_PRODUCCION` y crea un job `CONTENT-XXXXXX` una sola vez.

```bash
cd ~/PipeLine_Workflows
python3 -m services.idea_bank.cli generate --count 5
python3 -m services.idea_bank.cli list
python3 -m services.idea_bank.cli approve IDEA-000001
python3 -m unittest discover -s tests -v
```

La API escucha en `127.0.0.1:8090` desde Windows. La base se guarda en `data/ideas/ideas.db`; no requiere cuenta, clave ni servicio de Google.

## n8n workflows

Importa los JSON de `n8n/workflows/` desde n8n. Cuando la API esté saludable, activa los workflows de reposición mock, watcher de aprobaciones, planificador V3 y producción V4–V9. No hacen llamadas externas. Los paquetes V3 se guardan en data/jobs/CONTENT-ID/ y los medios en data/assets/CONTENT-ID/.

## Salud y backup

```bash
./scripts/health-check.sh
./scripts/backup-n8n.sh
```

El backup detiene servicios brevemente y guarda persistencia de n8n, datos y una copia privada de `.env` en `backups/`. Los backups contienen secretos; mantenlos en almacenamiento privado. `.env` y los backups están excluidos de Git.

## Estructura

- `infrastructure/`: infraestructura y configuración de servicios.
- `n8n/workflows/`: workflows JSON exportables.
- `services/`: módulos del pipeline, banco y worker local.
- `data/`: trabajos, ideas, assets y temporales (no se versionan).
- `logs/`: registros locales (no se versionan).
- `scripts/`: health-check y backup.
- `docs/`: documentación del proyecto.

## Planificador local V3

El planificador produce `plan.json`, `script.json`, `scenes.json` y `media_prompts.json` sin usar cuentas ni servicios externos. Consulta [docs/v3-local-planner.md](docs/v3-local-planner.md).

## Pipeline local V4–V9

El worker de producción usa imágenes mock, espeak-ng offline, FFmpeg, subtítulos que conservan el texto aprobado, metadata por plataforma, QA y buffer (mínimo 7, objetivo 14). No se conecta a Gemini, Google Cloud ni redes sociales. Publicar se limita a un dry-run explícito. Consulta [START.md](START.md), [STOP.md](STOP.md), [RECOVERY.md](RECOVERY.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md) y [docs/v4-v9-local-production.md](docs/v4-v9-local-production.md).
