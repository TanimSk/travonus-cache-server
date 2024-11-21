#!/bin/bash

# Navigate to the travonus_cache_server directory
cd travonus_cache_server || exit

# Define log file locations
LOG_DIR="../logs"  # Logs will be saved one level up from travonus_cache_server in a logs directory
mkdir -p "$LOG_DIR"  # Create the log directory if it doesn't exist
DJANGO_LOG="$LOG_DIR/django_server.log"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat.log"

# Start the Django development server
echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:7333 > "$DJANGO_LOG" 2>&1 &
DJANGO_PID=$!

# Start the Celery worker
echo "Starting Celery worker..."
celery -A travonus_cache_server worker -l INFO > "$CELERY_WORKER_LOG" 2>&1 &
CELERY_WORKER_PID=$!

# Start the Celery beat scheduler
echo "Starting Celery beat..."
celery -A travonus_cache_server beat -l INFO > "$CELERY_BEAT_LOG" 2>&1 &
CELERY_BEAT_PID=$!

# Function to kill all background processes
cleanup() {
    echo "Stopping all services..."
    kill $DJANGO_PID $CELERY_WORKER_PID $CELERY_BEAT_PID
}

# Trap EXIT signal to ensure cleanup is called when the script exits
trap cleanup EXIT

# Wait for all background processes to finish
wait
