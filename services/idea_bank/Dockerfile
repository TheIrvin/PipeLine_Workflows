FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY services /app/services
RUN mkdir -p /app/data/ideas && chown -R 1000:1000 /app
USER 1000:1000
EXPOSE 8090
CMD ["python", "-m", "services.idea_bank.api"]
