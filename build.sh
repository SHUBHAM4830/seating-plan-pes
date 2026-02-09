#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
python manage.py migrate

echo "Creating admin user..."
python create_admin.py

echo "Build completed successfully!"
