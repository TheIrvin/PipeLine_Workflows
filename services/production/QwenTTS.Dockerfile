FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg sox libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python -m pip install --no-cache-dir torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir \
    transformers==4.57.3 accelerate==1.12.0 librosa soundfile sox onnxruntime einops \
    && python -m pip install --no-cache-dir --no-deps qwen-tts==0.1.1
COPY services/production/qwen_tts_server.py /app/qwen_tts_server.py
COPY services/production/qwen_tts_infer.py /app/qwen_tts_infer.py
RUN useradd --create-home --uid 1000 worker
USER 1000:1000
EXPOSE 8092
CMD ["python", "/app/qwen_tts_server.py"]
