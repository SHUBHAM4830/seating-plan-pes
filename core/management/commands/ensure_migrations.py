"""
Management command to ensure migrations are applied.
This can be run manually or on startup.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
import sys


class Command(BaseCommand):
    help = 'Ensures all migrations are applied to the database'

    def handle(self, *args, **options):
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            self.stdout.write(self.style.SUCCESS('Database connection successful'))
            
            # Run migrations
            self.stdout.write('Running migrations...')
            call_command('migrate', verbosity=1, interactive=False)
            self.stdout.write(self.style.SUCCESS('Migrations completed'))
            
            # Create admin user if it doesn't exist
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if not User.objects.filter(username='admin').exists():
                self.stdout.write('Creating admin user...')
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='Admin123!'
                )
                self.stdout.write(self.style.SUCCESS('Admin user created'))
            else:
                self.stdout.write('Admin user already exists')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            sys.exit(1)
