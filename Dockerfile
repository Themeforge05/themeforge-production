FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY bundle.part00 bundle.part01 /tmp/
RUN cat /tmp/bundle.part00 /tmp/bundle.part01 | base64 -d | tar -xz -C /app \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir bcrypt==4.0.1 runwayml \
    && rm -f /tmp/bundle.part00 /tmp/bundle.part01
COPY patch_frontend.py /tmp/patch_frontend.py
RUN python /tmp/patch_frontend.py && rm -f /tmp/patch_frontend.py
COPY patch_instagram.py /tmp/patch_instagram.py
RUN python /tmp/patch_instagram.py && rm -f /tmp/patch_instagram.py
COPY patch_legal.py /tmp/patch_legal.py
RUN python /tmp/patch_legal.py && rm -f /tmp/patch_legal.py
COPY patch_tiktok_review.py /tmp/patch_tiktok_review.py
RUN python /tmp/patch_tiktok_review.py && rm -f /tmp/patch_tiktok_review.py
COPY patch_render.py /tmp/patch_render.py
RUN python /tmp/patch_render.py && rm -f /tmp/patch_render.py
COPY patch_production.py /tmp/patch_production.py
RUN python /tmp/patch_production.py && rm -f /tmp/patch_production.py
COPY patch_preview.py /tmp/patch_preview.py
RUN python /tmp/patch_preview.py && rm -f /tmp/patch_preview.py
COPY patch_cloud_platform.py /tmp/patch_cloud_platform.py
RUN python /tmp/patch_cloud_platform.py && rm -f /tmp/patch_cloud_platform.py
COPY patch_youtube_platform.py /tmp/patch_youtube_platform.py
RUN python /tmp/patch_youtube_platform.py && rm -f /tmp/patch_youtube_platform.py
ENV PYTHONUNBUFFERED=1
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
