FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services /app/services
RUN mkdir -p /app/data && chown -R 1000:1000 /app
USER 1000:1000
EXPOSE 8091
CMD ["python", "-m", "services.production.api"]
