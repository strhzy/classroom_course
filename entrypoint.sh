#!/bin/sh

echo "Ожидание базы данных..."

sleep 5

echo "Применение миграций..."
python manage.py migrate

echo "Создание суперпользователя..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin")
EOF

echo "Запуск сервера..."
exec daphne -b 0.0.0.0 -p 8000 classroom.asgi:application