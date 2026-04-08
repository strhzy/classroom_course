#!/bin/sh

echo "⏳ Ждём базу данных..."

sleep 5

echo "📦 Применяем миграции..."
python manage.py migrate

echo "👤 Создаём суперпользователя (если нужно)..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin")
EOF

echo "🚀 Запускаем сервер..."
exec daphne -b 0.0.0.0 -p 8000 classroom.asgi:application