# Pipeline automatizado de contenido

Base local del pipeline descrito en los prompts. n8n y el banco de ideas corren en Docker Desktop; la base de ideas SQLite reside en el filesystem de Ubuntu WSL.

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

Importa los JSON de `n8n/workflows/` desde n8n. Cuando la API esté saludable, activa los workflows de reposición mock, watcher de aprobaciones y planificador local. No hacen llamadas externas. Los paquetes V3 se guardan en `data/jobs/CONTENT-ID/`.

## Salud y backup

```bash
./scripts/health-check.sh
./scripts/backup-n8n.sh
```

El backup detiene servicios brevemente y guarda persistencia de n8n y el banco local en `backups/`. `.env` debe guardarse aparte en un lugar seguro: contiene la clave que cifra las credenciales de n8n. `.env` y los backups están excluidos de Git.

## Estructura

- `infrastructure/`: infraestructura y configuración de servicios.
- `n8n/workflows/`: workflows JSON exportables.
- `services/`: módulos del pipeline y API local del banco.
- `data/`: trabajos, ideas, assets y temporales (no se versionan).
- `logs/`: registros locales (no se versionan).
- `scripts/`: health-check y backup.
- `docs/`: documentación del proyecto.

## Planificador local V3

El planificador produce `plan.json`, `script.json`, `scenes.json` y `media_prompts.json` sin usar cuentas ni servicios externos. Consulta [docs/v3-local-planner.md](docs/v3-local-planner.md).
