"""
Management command to ensure migrations are applied.
This can be run manually or on startup.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
import sys
import os


class Command(BaseCommand):
    help = 'Ensures all migrations are applied to the database'

    def handle(self, *args, **options):
        try:
            self.stdout.write('=' * 50)
            self.stdout.write('Starting migration and setup process...')
            self.stdout.write('=' * 50)
            
            # Test database connection
            self.stdout.write('Testing database connection...')
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            self.stdout.write(self.style.SUCCESS('✓ Database connection successful'))
            
            # Run migrations with verbose output
            self.stdout.write('')
            self.stdout.write('Running database migrations...')
            self.stdout.write('-' * 50)
            call_command('migrate', verbosity=2, interactive=False)
            self.stdout.write('-' * 50)
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))
            
            # Create admin user if it doesn't exist
            self.stdout.write('')
            self.stdout.write('Checking admin user...')
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin123!')
            
            if not User.objects.filter(username=username).exists():
                self.stdout.write(f'Creating admin user "{username}"...')
                User.objects.create_superuser(username, email, password)
                self.stdout.write(self.style.SUCCESS(f'✓ Admin user "{username}" created successfully'))
            else:
                self.stdout.write(f'Admin user "{username}" already exists')
            
            self.stdout.write('')
            self.stdout.write('=' * 50)
            self.stdout.write(self.style.SUCCESS('✓ Setup completed successfully!'))
            self.stdout.write('=' * 50)
                
        except Exception as e:
            self.stdout.write('')
            self.stdout.write('=' * 50)
            self.stdout.write(self.style.ERROR('✗ ERROR OCCURRED'))
            self.stdout.write('=' * 50)
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            self.stdout.write('=' * 50)
            sys.exit(1)
