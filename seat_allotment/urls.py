from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    # Admin Custom URL
    path('pesce_examsee_1962/', views.admin_login, name='admin_login'),
    
    # Public Student View
    path('', views.index, name='index'),
    path('allotment/', views.index, name='allotment'),

    # Admin Dashboard & Operations
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('upload/', views.upload_file, name='upload_file'),
    path('preview/', views.preview_data, name='preview_data'),
    path('delete/<int:upload_id>/', views.delete_upload, name='delete_upload'),
    
    # Student API
    path('api/allotment', views.student_lookup, name='student_lookup'),

    # Default Admin - Re-enabled per user request
    path('secret_admin_dashboard_99/', admin.site.urls),
    
    # Logout
    path('logout/', views.logout_view, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
