# Iniciar el pipeline local

En Ubuntu/WSL:
~~~bash
cd ~/PipeLine_Workflows
git submodule update --init --recursive
docker compose up -d --build
docker compose ps
~~~

Panel de ideas: http://localhost:8090
n8n: http://localhost:5678
Health del worker: http://localhost:8091/healthz

Aprueba una idea desde el panel. Los workflows crean el job, generan el paquete y continúan hasta QA READY. La publicación real permanece desactivada.

El primer uso de subtítulos con voz descarga Whisper base para CPU en `data/models`. Esa descarga necesita conexión a Internet y se reutiliza en las siguientes ejecuciones. El servicio no publica el puerto del subtitulador a la red local; el worker lo consume dentro de Docker.
