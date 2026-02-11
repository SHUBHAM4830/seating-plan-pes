from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta, datetime
import os
import json
import logging

from .models import UploadedFile, SeatAllotment, VisibilityWindow, AdminAuditLog
from .parser import parse_exam_file_wrapper

logger = logging.getLogger(__name__)

# ================= PUBLIC VIEWS =================
def index(request):
    return render(request, 'index.html')

# ================= ADMIN VIEWS =================

def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if not username or not password:
                messages.error(request, "Username and password are required")
                return render(request, 'admin_login.html')
            
            logger.info(f"Login attempt for username: {username}")
            
            # Test database connection before authentication
            try:
                from django.db import connection
                connection.ensure_connection()
                logger.info("Database connection successful")
            except Exception as db_error:
                logger.error(f"Database connection failed: {str(db_error)}", exc_info=True)
                messages.error(request, "Database connection error. Please contact administrator.")
                return render(request, 'admin_login.html')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None and user.is_staff:
                login(request, user)
                logger.info(f"Successful login for user: {username}")
                return redirect('admin_dashboard')
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                messages.error(request, "Invalid credentials")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred during login. Please try again.")
            
    return render(request, 'admin_login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('admin_login')

from django.http import JsonResponse, HttpResponseForbidden, Http404

# ... (imports remain similar, just adding Http404 to line 5 or wherever likely)

@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not request.user.is_staff:
        raise Http404
    cleanup_expired_data()
    # ...

# Actually, defining a custom decorator is cleaner.
# But for now, user asked to "return 404".
# Let's modify the imports and the specific views.

def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404
    
    cleanup_expired_data()
    uploads = UploadedFile.objects.all().order_by('-uploaded_at')
    
    dashboard_data = []
    now = timezone.now()
    
    for upload in uploads:
        status = "Inactive"
        if hasattr(upload, 'visibility_window'):
            win = upload.visibility_window
            if win.visible_until < now:
                status = "Expired"
            elif win.visible_from <= now <= win.visible_until and win.is_active_manual:
                status = "Active"
            elif win.visible_from > now:
                status = "Upcoming"
            
            if not win.is_active_manual and status != "Expired":
                 status = "Deactivated (Manual)"
        
        dashboard_data.append({
            'file': upload,
            'status': status,
            'window': getattr(upload, 'visibility_window', None)
        })
        
    return render(request, 'dashboard.html', {'uploads': dashboard_data})

def upload_file(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404

    if request.method == 'POST' and request.FILES.getlist('file'):
        files = request.FILES.getlist('file')
        
        all_pages = []
        upload_ids = []
        
        for file in files:
            if not file.name.endswith('.docx'):
                messages.error(request, f"Skipped {file.name}: Only .docx files allowed.")
                continue
                
            # ContentType check - simplistic but kept from before
            if file.content_type != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                # messages.warning(request, f"Warning: {file.name} might not be a valid DOCX.")
                pass
                
            upload_obj = UploadedFile.objects.create(file=file)
            upload_ids.append(upload_obj.id)
            AdminAuditLog.objects.create(user=request.user, action='UPLOAD', details=f"Uploaded {file.name}")
            
            file_path = upload_obj.file.path
            result = parse_exam_file_wrapper(file_path)
            
            if "error" in result and result["error"]:
                 messages.error(request, f"Error parsing {file.name}: {result['error']}")
                 upload_obj.delete()
                 upload_ids.remove(upload_obj.id)
                 continue

            # Tag pages with source info
            file_pages = result.get('pages', [])
            for page in file_pages:
                page['upload_id'] = upload_obj.id
                page['filename'] = file.name
                all_pages.append(page)
        
        if not all_pages:
            return redirect('admin_dashboard')

        # Store aggregated pages
        request.session['parsed_pages'] = all_pages
        request.session['upload_ids'] = upload_ids
        
        return redirect('preview_data')
        
    return redirect('admin_dashboard')

def preview_data(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404

    pages = request.session.get('parsed_pages', [])
    upload_ids = request.session.get('upload_ids', [])
    
    # Fallback for legacy single upload session if any
    if not upload_ids and request.session.get('upload_id'):
        upload_ids = [request.session.get('upload_id')]
    
    if not pages or not upload_ids:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # --- PUBLISH ACTION ---
        if action == 'publish':
            exam_date = request.POST.get('exam_date')
            window_name_input = request.POST.get('window_name') 
            
            try:
                if not exam_date: raise ValueError("Date required")
                exam_dt = datetime.strptime(exam_date, '%Y-%m-%dT%H:%M') 
                exam_dt = timezone.make_aware(exam_dt)
            except Exception as e:
                messages.error(request, f"Invalid date format: {e}")
                return redirect('preview_data')

            # 1. Create SeatAllotments
            # We need to map upload_id to UploadedFile objects to avoid repeated DB hits
            upload_objs = {u.id: u for u in UploadedFile.objects.filter(id__in=upload_ids)}
            
            records_to_create = []
            
            for page in pages:
                uid = page.get('upload_id')
                if not uid or uid not in upload_objs: continue
                
                u_obj = upload_objs[uid]
                room = page.get('room', 'UNKNOWN')
                
                for record in page.get('records', []):
                    records_to_create.append(SeatAllotment(
                        uploaded_file=u_obj,
                        usn=record.get('usn', 'UNKNOWN'),
                        room_no=room, 
                        seat_no=record.get('seat', 'UNKNOWN'),
                        course_code=record.get('course', 'UNKNOWN'),
                        exam_start_time=exam_dt,
                        other_data=record.get('raw_data', [])
                    ))
            
            SeatAllotment.objects.bulk_create(records_to_create)
            
            # 2. Create VisibilityWindows & Update UploadedFiles
            for uid, u_obj in upload_objs.items():
                w_name = window_name_input if window_name_input else u_obj.filename()
                
                VisibilityWindow.objects.create(
                    file=u_obj,
                    window_name=w_name,
                    visible_from=exam_dt - timedelta(minutes=45),
                    visible_until=exam_dt + timedelta(hours=3),
                    is_active_manual=True
                )
                
                u_obj.is_published = True
                u_obj.exam_date = exam_dt.date()
                u_obj.save()
                AdminAuditLog.objects.create(user=request.user, action='PUBLISH', details=f"Published {u_obj.filename()}")
            
            # Cleanup Session
            request.session.pop('parsed_pages', None)
            request.session.pop('upload_ids', None)
            request.session.pop('upload_id', None)
            
            messages.success(request, f"Published {len(upload_ids)} files successfully!")
            return redirect('admin_dashboard')

        # --- UPDATE PAGE ROOM ---
        elif action == 'update_page_room':
            try:
                page_idx = int(request.POST.get('page_idx'))
                new_room = request.POST.get('room_no')
                
                # Find page by index (assuming order is preserved)
                # parser uses block_index which might not be 0..N perfectly if empty blocks skipped
                # better to iterate and match 'page_idx' stored in dict
                
                target_page = next((p for p in pages if p['page_idx'] == page_idx), None)
                if target_page:
                    target_page['room'] = new_room
                    request.session['parsed_pages'] = pages # Save back
                    messages.success(request, "Room updated for page.")
            except:
                messages.error(request, "Error updating room.")
                
            return redirect('preview_data')

        # --- UPDATE SINGLE RECORD ---
        elif action == 'update_record':
            try:
                page_idx = int(request.POST.get('page_idx'))
                row_idx = int(request.POST.get('row_idx'))
                new_usn = request.POST.get('usn')
                new_seat = request.POST.get('seat')
                
                target_page = next((p for p in pages if p['page_idx'] == page_idx), None)
                if target_page:
                    if 0 <= row_idx < len(target_page['records']):
                        target_page['records'][row_idx]['usn'] = new_usn
                        target_page['records'][row_idx]['seat'] = new_seat
                        request.session['parsed_pages'] = pages # Save back
                        messages.success(request, "Record updated.")
            except:
                messages.error(request, "Error updating record.")
                
            return redirect('preview_data')

    # Calculate total for display
    total_count = sum(len(p['records']) for p in pages)
    return render(request, 'preview.html', {'pages': pages, 'count': total_count})

def delete_upload(request, upload_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        raise Http404

    if request.method == 'POST':
        upload = get_object_or_404(UploadedFile, id=upload_id)
        filename = upload.filename()
        upload.delete()
        AdminAuditLog.objects.create(user=request.user, action='DELETE', details=f"Deleted {filename}")
        messages.success(request, "Deleted successfully")
    return redirect('admin_dashboard')

# ================= UTILS =================
def cleanup_expired_data():
    now = timezone.now()
    expired_windows = VisibilityWindow.objects.filter(visible_until__lt=now)
    for win in expired_windows:
        win.file.delete()

# ================= STUDENT VIEWS =================
def student_lookup(request):
    usn = request.GET.get('usn')
    if not usn:
        return JsonResponse({'error': 'USN required'}, status=400)
    
    now = timezone.now()
    allotment = SeatAllotment.objects.filter(
        usn__iexact=usn,
        uploaded_file__visibility_window__visible_from__lte=now,
        uploaded_file__visibility_window__visible_until__gte=now,
        uploaded_file__visibility_window__is_active_manual=True
    ).select_related('uploaded_file').first()
    
    if allotment:
        # Get start time in local timezone (Asia/Kolkata check)
        # Django handles timezone conversion if USE_TZ is True
        localized_time = timezone.localtime(allotment.exam_start_time)
        return JsonResponse({
            "usn": allotment.usn,
            "room": allotment.room_no,
            "seat": allotment.seat_no,
            "course_code": allotment.course_code or "N/A",
            "exam_time": localized_time.isoformat(),
        })
    else:
        return JsonResponse({'message': 'Allotment not found'}, status=404)
