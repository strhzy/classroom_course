#!/bin/sh
set -e

_clamav_enabled() {
  case "${CLAMAV_ENABLED:-}" in 1|true|True|yes|YES|on|ON) return 0 ;; *) return 1 ;; esac
}

if _clamav_enabled; then
  echo "ClamAV: обновление баз (freshclam), первый запуск может занять несколько минут..."
  freshclam --stdout || echo "ClamAV: freshclam завершился с ошибкой (проверьте сеть); clamd может не стартовать без баз."
  echo "ClamAV: запуск clamd..."
  mkdir -p /var/run/clamav /var/log/clamav
  clamd &
  _sock="${CLAMAV_SOCKET_PATH:-/var/run/clamav/clamd.ctl}"
  echo "ClamAV: ожидание сокета ${_sock}..."
  _i=0
  while [ ! -S "$_sock" ]; do
    _i=$((_i + 1))
    if [ "$_i" -gt 120 ]; then
      echo "ClamAV: таймаут ожидания clamd; приложение стартует, проверка может быть недоступна."
      break
    fi
    sleep 1
  done
  if [ -S "$_sock" ]; then
    echo "ClamAV: clamd готов."
  fi
fi

if [ "$DJANGO_USE_SQLITE" = "true" ] || [ "$DJANGO_USE_SQLITE" = "1" ]; then
  echo "Режим SQLite — пропуск ожидания PostgreSQL и Redis."
else
  if [ "$DJANGO_DOCKER_HOST_NETWORK" = "true" ] || [ "$DJANGO_DOCKER_HOST_NETWORK" = "1" ]; then
    _pg_wait="${POSTGRES_HOST:-127.0.0.1}"
  else
    _pg_wait="${POSTGRES_HOST:-db}"
    case "$_pg_wait" in
      localhost|127.0.0.1|"") _pg_wait=db ;;
    esac
  fi
  echo "Ожидание PostgreSQL (${_pg_wait}:${POSTGRES_PORT:-5432})..."
  until pg_isready -h "$_pg_wait" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-classroom}" >/dev/null 2>&1; do
    sleep 1
  done
  echo "PostgreSQL доступен."

  echo "Ожидание Redis..."
  _redis_parse="$(python3 -c "import os; from urllib.parse import urlparse; p=urlparse(os.getenv('REDIS_URL','redis://127.0.0.1:6379/0')); print((p.hostname or '127.0.0.1'), (p.port or 6379))")"
  _rh=$(echo "$_redis_parse" | awk '{print $1}')
  _rp=$(echo "$_redis_parse" | awk '{print $2}')
  if [ "$DJANGO_DOCKER_HOST_NETWORK" != "true" ] && [ "$DJANGO_DOCKER_HOST_NETWORK" != "1" ]; then
    case "$_rh" in
      localhost|127.0.0.1|"") _rh=redis ;;
    esac
  fi
  until redis-cli -h "$_rh" -p "$_rp" ping 2>/dev/null | grep -q PONG; do
    sleep 1
  done
  echo "Redis доступен."
fi

echo "Миграции..."
python manage.py migrate --noinput

if [ -n "$DJANGO_SITE_DOMAIN" ]; then
  echo "django.contrib.sites: запись id=1, domain=$DJANGO_SITE_DOMAIN (OAuth / allauth)"
  python manage.py shell -c 'from django.contrib.sites.models import Site as S; import os; d=os.environ["DJANGO_SITE_DOMAIN"].strip(); nm=os.getenv("DJANGO_SITE_NAME", "Classroom"); S.objects.update_or_create(pk=1, defaults={"domain": d, "name": nm})'
fi

echo "Проверка суперпользователя (первый запуск)..."
python scripts/docker_bootstrap_superuser.py

echo "Запуск ASGI (Daphne)..."
exec daphne -b 0.0.0.0 -p 8000 classroom.asgi:application
