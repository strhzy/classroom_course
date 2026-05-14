FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=classroom.settings \
    DJANGO_RUNNING_IN_CONTAINER=1 \
    PIP_NO_CACHE_DIR=1 \
    CLAMAV_ENABLED=1 \
    CLAMAV_FAIL_OPEN=1 \
    CLAMAV_SOCKET_PATH=/var/run/clamav/clamd.ctl

RUN printf 'Acquire::http::Timeout "120";\nAcquire::Retries "5";\n' > /etc/apt/apt.conf.d/99network

# Клиент PostgreSQL той же мажорной версии, что и сервер (compose: postgres:16*), иначе pg_dump/pg_restore
# падают с «server version mismatch».
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client-16 \
        redis-tools \
        clamav-daemon \
        clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

# ClamAV: разрешить запуск (Example no), демон и сигнатуры от root — как в образе и приложение.
RUN set -e; \
    for f in /etc/clamav/clamd.conf /etc/clamav/freshclam.conf; do \
        sed -i 's/^Example$/Example no/' "$f"; \
        sed -i 's/^#Example$/Example no/' "$f"; \
    done; \
    sed -i -E 's/^#?User[[:space:]]+clamav/User root/' /etc/clamav/clamd.conf; \
    sed -i -E 's/^#?DatabaseOwner[[:space:]]+clamav/DatabaseOwner root/' /etc/clamav/freshclam.conf; \
    if grep -q '^LocalSocketMode' /etc/clamav/clamd.conf; then \
        sed -i 's/^LocalSocketMode.*/LocalSocketMode 666/' /etc/clamav/clamd.conf; \
    else \
        echo 'LocalSocketMode 666' >> /etc/clamav/clamd.conf; \
    fi; \
    mkdir -p /var/run/clamav /var/lib/clamav /var/log/clamav; \
    chmod 755 /var/run/clamav /var/lib/clamav

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static /app/media \
    && chmod +x /app/entrypoint.sh

RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
