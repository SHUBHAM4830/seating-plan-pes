from django.db import models
from django.contrib.auth.models import User
import os

class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    exam_date = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)

    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return f"{self.filename()} ({self.uploaded_at})"

class SeatAllotment(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='allotments')
    usn = models.CharField(max_length=20, db_index=True)
    room_no = models.CharField(max_length=50)
    seat_no = models.CharField(max_length=50)
    course_code = models.CharField(max_length=50, blank=True, null=True)
    exam_start_time = models.DateTimeField()
    
    # Store dynamic fields as JSON if needed, but for now simple structure is requested.
    # Given requirements say "Class or section or mark fields (format is dynamic)", 
    # we might need a JSONField or similar if we were using Postgres, 
    # but with SQLite/Django we can use a TextField with JSON content or just simple fields if structured.
    # The requirement says "return JSON similar to... Field names like class or mark are dynamic".
    # Let's add a JSONField for dynamic data to be safe and flexible.
    other_data = models.JSONField(default=dict, blank=True)

    class Meta:
        # Constraint: Unique USN per exam session? 
        # The requirement says "USN must be unique" but arguably across different exams it might appear.
        # "USN must be unique" likely means per uploaded file or generally. 
        # Given "Single database", "Student Layout", let's assume USN is unique PER EXAM SESSION.
        # But rigorous uniqueness might be "USN" globally if it's a student lookup for "current active exam".
        # Let's stick to USN indexed as requested. 
        indexes = [
            models.Index(fields=['usn']),
        ]

    def __str__(self):
        return f"{self.usn} - {self.room_no}"

class VisibilityWindow(models.Model):
    file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE, related_name='visibility_window')
    window_name = models.CharField(max_length=255, blank=True)
    visible_from = models.DateTimeField()
    visible_until = models.DateTimeField()
    is_active_manual = models.BooleanField(default=True) # For manual activation/deactivation override if needed

    def __str__(self):
        return f"Window for {self.file.filename()}"

class AdminAuditLog(models.Model):
    ACTION_CHOICES = [
        ('UPLOAD', 'Upload'),
        ('UPDATE', 'Update'),
        ('PUBLISH', 'Publish'),
        ('ACTIVATE', 'Activate'),
        ('DEACTIVATE', 'Deactivate'),
        ('DELETE', 'Delete'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True) # JSON or text description

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
