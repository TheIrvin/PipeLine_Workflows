# Iniciar el pipeline local

En Ubuntu/WSL:
~~~bash
cd ~/PipeLine_Workflows
docker compose up -d --build
docker compose ps
~~~

Panel de ideas: http://localhost:8090
n8n: http://localhost:5678
Health del worker: http://localhost:8091/healthz

Aprueba una idea desde el panel. Los workflows crean el job, generan el paquete y continúan hasta QA READY. La publicación real permanece desactivada.
