release: python manage.py migrate && python create_admin.py
web: gunicorn seat_allotment.wsgi
