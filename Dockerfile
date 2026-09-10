FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY bundle.part00 bundle.part01 /tmp/
RUN cat /tmp/bundle.part00 /tmp/bundle.part01 | base64 -d | tar -xz -C /app \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir bcrypt==4.0.1 \
    && rm -f /tmp/bundle.part00 /tmp/bundle.part01
COPY patch_frontend.py /tmp/patch_frontend.py
RUN python /tmp/patch_frontend.py && rm -f /tmp/patch_frontend.py
ENV PYTHONUNBUFFERED=1
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
