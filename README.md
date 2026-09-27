# Pipeline local de contenido

Pipeline local para proponer ideas, redactar guiones en español, recibir imágenes o videos creados manualmente, añadir narración y subtítulos, y dejar el MP4 final listo para revisar. Está pensado para Windows con WSL2/Ubuntu y Docker Desktop. No necesita Google Cloud ni claves de Gemini/OpenAI: las imágenes y clips se generan manualmente en las interfaces web que cada usuario tenga disponibles.

## Repositorios

- **Este pipeline:** [TheIrvin/PipeLine_Workflows](https://github.com/TheIrvin/PipeLine_Workflows)
- **Editor y backend de subtítulos:** [TheIrvin/Subtitulador-de-videos-en-Espanol-e-Ingles-9-16](https://github.com/TheIrvin/Subtitulador-de-videos-en-Espanol-e-Ingles-9-16). Se incluye como submódulo en `integrations/subtitle-editor/`; Docker construye el servicio de subtítulos desde ese código.

Clona con submódulos para obtener ambos repositorios y la versión enlazada del subtitulador.

## Requisitos

- Windows 11 con WSL2 y una distribución Ubuntu. En Docker Desktop, habilita la integración WSL para Ubuntu.
- Docker Desktop con Docker Compose v2 (`docker compose version`). Ollama, FFmpeg, faster-whisper, Qwen3-TTS y n8n corren dentro de contenedores; no hace falta instalarlos por separado en Windows.
- Git instalado dentro de Ubuntu/WSL, con acceso a GitHub para clonar ambos repositorios.
- Internet y espacio libre durante la primera instalación: Docker descarga imágenes y el pipeline baja los modelos locales de Ollama, Hugging Face y Whisper cuando se necesitan. La síntesis corre en CPU con la configuración incluida; puede tardar más y consumir varios GB de RAM y disco. No se ha fijado un mínimo de hardware.
- Un audio de referencia y su transcripción exacta para el proveedor de voz local predeterminado, Qwen3-TTS. Si no tienes esos archivos, puedes cambiar `TTS_PROVIDER` a `espeak-ng` en `.env`. La muestra y transcripción son privadas y no están incluidas en Git.
- Acceso manual a una herramienta web para generar imágenes y clips (por ejemplo Gemini). El pipeline entrega los prompts y procesa los archivos; no automatiza el navegador ni garantiza cuotas gratuitas de terceros.

> El flujo documentado usa Windows + WSL2. En Linux se puede usar Docker Compose configurando `MEDIA_INBOX_HOST_PATH` con una ruta local absoluta. macOS no es un destino validado actualmente.

## Instalación desde cero

Abre Ubuntu/WSL y ejecuta:

```bash
git clone --recurse-submodules https://github.com/TheIrvin/PipeLine_Workflows.git
cd PipeLine_Workflows
cp .env.example .env
```

Genera una clave aleatoria local para n8n y pégala como valor de `N8N_ENCRYPTION_KEY` dentro de `.env`:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Configura también el usuario y grupo de Ubuntu/WSL para que los archivos montados desde `videos/` y `data/` queden editables por tu cuenta:

```bash
sed -i "s/^PIPELINE_UID=.*/PIPELINE_UID=$(id -u)/" .env
sed -i "s/^PIPELINE_GID=.*/PIPELINE_GID=$(id -g)/" .env
```

El valor inicial de `MEDIA_INBOX_HOST_PATH` es `./videos`. Esa ruta es relativa a la raíz del repositorio y crea la carpeta compartida que usa el worker. Para guardarla en otro disco o directorio, reemplaza ese valor en `.env` por la ruta absoluta correspondiente al host; en WSL normalmente será una ruta como `/mnt/c/Users/<tu_usuario>/Videos/Pipeline`.

Construye e inicia los servicios:

```bash
docker compose up -d --build
docker compose ps
./scripts/health-check.sh
```

La primera ejecución descarga las imágenes y modelos y puede tardar. Revisa `docker compose logs -f` si un servicio todavía no está saludable. Abre:

- Banco de ideas: <http://localhost:8090>
- n8n: <http://localhost:5678> (crea el usuario propietario la primera vez)
- Worker: <http://localhost:8091/healthz>

### Configurar los workflows de n8n

Los workflows se importan desactivados para evitar que empiecen a trabajar antes de configurar el entorno. En n8n, importa desde archivo y activa los cuatro JSON de `n8n/workflows/`:

1. `idea-replenisher.json` — repone el banco de ideas.
2. `idea-approval-watcher.json` — crea el trabajo cuando se aprueba una idea.
3. `planner-worker.json` — genera guion y prompts.
4. `production-worker.json` — espera los medios y ejecuta narración, montaje, subtítulos y QA.

No se conectan a APIs de redes sociales ni a servicios de generación de imagen. Sus detalles están en [`n8n/workflows/README.md`](n8n/workflows/README.md).

## Modelos locales y voz

El stack trae estos componentes; no necesitas descargar aplicaciones de IA por separado:

- **Ollama + `qwen3:4b`:** propone ideas y redacta guiones localmente. Compose descarga el modelo al iniciar.
- **Qwen3-TTS `Qwen/Qwen3-TTS-12Hz-0.6B-Base`:** sintetiza la voz localmente y permite clonarla con una muestra. El contenedor usa CPU; el modelo de Hugging Face se descarga al primer uso.
- **Subtitulador del repositorio enlazado + faster-whisper `base`:** detecta tiempos y aplica los subtítulos en el worker local. La descarga inicial de Whisper necesita Internet.
- **FFmpeg:** normaliza el video a vertical 9:16, mezcla el audio y prepara el master.

Para clonar tu voz, coloca tus propios archivos en la carpeta local ignorada por Git:

```text
data/models/voice-reference/Audio_Ejemplo.mp3
data/models/voice-reference/Audio_Ejemplo.txt
```

El `.txt` debe contener la transcripción fiel del audio. Si usas otros nombres o ubicaciones, actualiza `QWEN_TTS_REFERENCE_AUDIO` y `QWEN_TTS_REFERENCE_TEXT_FILE` en `.env`. No subas muestras de voz ni credenciales al repositorio. También puedes elegir `espeak-ng` como voz sintética local. `fish-audio` es una integración opcional que requiere configurar manualmente su clave y los valores `FISH_AUDIO_*` en `.env`.

## Flujo de trabajo

Para las decisiones de referencia, composición, movimiento y recuperación de errores, consulta la [skill de imágenes y animación](.agents/skills/pipeline-visual-media/SKILL.md).

1. Abre el banco de ideas, revisa las propuestas y aprueba una.
2. El planificador local crea un trabajo `CONTENT-XXXXXX` y sus guiones y prompts.
3. Abre `videos/subir/CONTENT-XXXXXX/`. El worker crea allí `LEEME.txt`, `imagenes/` y `animar_imagenes/`.
4. Genera cada imagen con su prompt y la referencia de personaje real. Después usa esa imagen como referencia al generar el clip con el prompt de animación correspondiente.
5. Entrega los medios de una de estas formas:
   - **MP4 completo editado por ti:** guárdalo como `video_completo.mp4` en la raíz de `videos/subir/CONTENT-XXXXXX/`.
   - **Clips separados:** guárdalos como `clip_01.mp4`, `clip_02.mp4`, etc. en `videos/subir/CONTENT-XXXXXX/animar_imagenes/` (también se aceptan en la raíz del trabajo). El worker los combina según el orden y el tiempo objetivo de cada escena. Para ajustar a mano la pausa y el ritmo de cada corte, únelos antes y entrega `video_completo.mp4`.

   Si encuentra `video_completo.mp4`, lo prioriza sobre los clips separados. Usa un solo método de entrega por trabajo para evitar confusiones. Los archivos originales de `subir` se conservan para permitir reintentos.
6. El worker usa el guion aprobado para generar voz local, sincronizar los subtítulos, crear el master vertical y revisar calidad.
7. Si QA pasa, copia el resultado final a `videos/terminado/CONTENT-XXXXXX.mp4`. El master de trabajo y los demás archivos siguen disponibles en `data/assets/CONTENT-XXXXXX/`.

La carpeta del proyecto se puede abrir desde Windows con el Explorador de archivos usando la ruta WSL de tu instalación. Desde Ubuntu, estando en la raíz del repositorio, ejecuta:

```bash
explorer.exe "$(wslpath -w "$PWD/videos")"
```

Estructura esperada:

```text
PipeLine_Workflows/
├── videos/
│   ├── subir/
│   │   └── CONTENT-XXXXXX/
│   │       ├── LEEME.txt
│   │       ├── imagenes/
│   │       └── animar_imagenes/
│   └── terminado/
│       └── CONTENT-XXXXXX.mp4
├── data/
│   ├── ideas/
│   ├── jobs/
│   ├── assets/
│   └── models/
└── integrations/
    └── subtitle-editor/  # submódulo del segundo repositorio
```

`videos/subir/` y `videos/terminado/` se crean al iniciar y están excluidas de Git salvo sus marcadores de carpeta vacía. Los datos, modelos, audio de referencia y resultados son locales.

## Comandos diarios

Desde la raíz del repo en Ubuntu:

```bash
docker compose ps
docker compose logs -f production-worker
docker compose stop       # detener sin borrar datos
docker compose start      # reanudar
```

Para actualizar una copia existente:

```bash
git pull --recurse-submodules
git submodule update --init --recursive
docker compose up -d --build
```

## Privacidad y límites

- Ideas, guiones, voz, video, subtítulos y modelos permanecen en el equipo. No se publica nada automáticamente.
- Generar imágenes y clips es una tarea manual en el servicio web que elijas. Los límites, funciones, idiomas y disponibilidad dependen de ese proveedor y de la cuenta.
- Qwen3-TTS requiere audio y transcripción de referencia para clonación local. No copies esos datos a issues, prompts públicos ni Git.
- El `.env` incluye la clave local de cifrado de n8n y puede contener otras credenciales: mantenlo privado.
- Las publicaciones de redes sociales están en modo `dry-run`; este flujo no inicia sesión ni publica.

## Solución de problemas

- Servicios: `docker compose ps` y `docker compose logs --tail=150 production-worker`.
- Salud general: `./scripts/health-check.sh`.
- Revisa que el job tenga `video_completo.mp4` o todos los `clip_XX.mp4` requeridos dentro de su carpeta en `videos/subir/`.
- Verifica MP4s incompletos o corruptos antes de reanudar. El worker valida los archivos con `ffprobe`.
- Para retomar un job después de corregirlo, llama `POST http://localhost:8091/api/jobs/CONTENT-XXXXXX/resume`.
- Guías: [`START.md`](START.md), [`STOP.md`](STOP.md), [`RECOVERY.md`](RECOVERY.md), [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) y [`docs/v4-v9-local-production.md`](docs/v4-v9-local-production.md).
