from django.contrib import admin
from .models import UploadedFile, SeatAllotment, VisibilityWindow, AdminAuditLog

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'uploaded_at', 'is_published', 'exam_date')
    list_filter = ('is_published', 'uploaded_at')

@admin.register(SeatAllotment)
class SeatAllotmentAdmin(admin.ModelAdmin):
    list_display = ('usn', 'subject_code', 'room_no', 'seat_no', 'exam_start_time', 'uploaded_file')
    search_fields = ('usn', 'room_no', 'course_code')
    list_filter = ('exam_start_time', 'room_no')
    
    def subject_code(self, obj):
        return obj.course_code

@admin.register(VisibilityWindow)
class VisibilityWindowAdmin(admin.ModelAdmin):
    list_display = ('window_name', 'file', 'visible_from', 'visible_until', 'is_active_manual')
    list_filter = ('is_active_manual', 'visible_from')

@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'details')
    list_filter = ('action', 'timestamp')
    search_fields = ('details', 'user__username')
