FROM python:3.12-slim

# Genie-TTS 2.0.2 server for 小满 (xiaoman) — ONNX inference only, no torch needed.
# pip uses the Tsinghua mirror (PyPI official is ~39KB/s from this server).

RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g; s|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; \
    sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g; s|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true; \
    apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libportaudio2 \
    ffmpeg \
    curl \
    procps \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV GENIE_DATA_DIR=/app/genie-data/GenieData
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    "genie-tts==2.0.2" "onnxruntime==1.22.1"

WORKDIR /app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
