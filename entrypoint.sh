#!/bin/bash
set -e


# Control migrations via environment variable MIGRATE_ON_STARTUP (default true)
#if [ "${MIGRATE_ON_STARTUP:-true}" = "true" ]; then
#  echo "Running makemigrations and migrate..."
#  python manage.py makemigrations --noinput
#  python manage.py migrate --noinput
#else
#  echo "Skipping migrations on startup."
#fi

#echo "Collecting static files..."
#python manage.py collectstatic --noinput

echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000


#echo "Starting Django ASGI server with Gunicorn + Uvicorn workers..."
#exec gunicorn traventic_core.asgi:application \
#    -k uvicorn.workers.UvicornWorker \
#    --workers 4 \
#    --bind 0.0.0.0:8000 \
#    --timeout 120 \
#    --log-level info
