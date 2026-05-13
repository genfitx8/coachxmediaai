FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        imagemagick \
        libsm6 \
        libxext6 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && if [ -f /etc/ImageMagick-6/policy.xml ]; then \
        sed -i 's#<policy domain="path" rights="none" pattern="@\*"/>##' /etc/ImageMagick-6/policy.xml; \
        sed -i 's#rights="none" pattern="PDF"#rights="read|write" pattern="PDF"#' /etc/ImageMagick-6/policy.xml; \
    fi

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
