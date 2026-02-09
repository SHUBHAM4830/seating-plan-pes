import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seat_allotment.settings')
django.setup()

try:
    from django.contrib.auth import get_user_model
    from django.db import OperationalError
    
    User = get_user_model()
    
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin123!')
    
    try:
        if not User.objects.filter(username=username).exists():
            print(f"Creating superuser '{username}'...")
            User.objects.create_superuser(username, email, password)
            print(f"Superuser '{username}' created successfully!")
        else:
            print(f"Superuser '{username}' already exists.")
    except OperationalError as e:
        print(f"Database error occurred: {e}")
        print("Skipping superuser creation due to database connection issue.")
    except Exception as e:
        print(f"An error occurred during superuser creation: {e}")
        
except ImportError as e:
    print(f"Error importing Django modules: {e}")
