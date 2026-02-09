#!/usr/bin/env bash
# Script to manually run migrations on Render
# This can be run via Render's shell/console feature

echo "Running database migrations..."
python manage.py migrate

echo "Creating admin user..."
python create_admin.py

echo "Done!"
