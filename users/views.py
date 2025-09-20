# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from burnermanagement.firebase_auth import FirebaseAdminManager
from venues.models import Venue
import logging

logger = logging.getLogger(__name__)

class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'users/profile.html'

@login_required
def admin_management(request):
    """Admin user management interface (site admins only)"""
    if not request.user.is_site_admin():
        messages.error(request, "Only site administrators can manage admin users")
        return redirect('core:home')
    
    try:
        manager = FirebaseAdminManager()
        all_admin_users = manager.list_admin_users()
        venues = Venue.get_all_active()
        
        # Filter by role if specified
        role_filter = request.GET.get('role', '')
        if role_filter and role_filter in ['siteAdmin', 'venueAdmin', 'subAdmin']:
            admin_users = [u for u in all_admin_users if u.get('role') == role_filter]
        else:
            admin_users = all_admin_users
        
        # Search functionality
        search = request.GET.get('search', '').strip()
        if search:
            admin_users = [u for u in admin_users if 
                          search.lower() in u.get('email', '').lower() or
                          search.lower() in u.get('displayName', '').lower()]
        
        # Pagination
        paginator = Paginator(admin_users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Stats
        stats = {
            'total': len(all_admin_users),
            'site_admins': len([u for u in all_admin_users if u.get('role') == 'siteAdmin']),
            'venue_admins': len([u for u in all_admin_users if u.get('role') == 'venueAdmin']),
            'sub_admins': len([u for u in all_admin_users if u.get('role') == 'subAdmin']),
            'active': len([u for u in all_admin_users if u.get('isActive', True) and not u.get('disabled', False)]),
        }
        
        context = {
            'page_obj': page_obj,
            'venues': venues,
            'search': search,
            'role_filter': role_filter,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error loading admin management: {e}")
        messages.error(request, "Failed to load admin users. Please check Firebase connection.")
        context = {
            'page_obj': None,
            'venues': [],
            'search': '',
            'role_filter': '',
            'stats': {'total': 0, 'site_admins': 0, 'venue_admins': 0, 'sub_admins': 0, 'active': 0}
        }
    
    return render(request, 'users/admin_management.html', context)

@login_required
@require_http_methods(["POST"])
def create_admin_user(request):
    """Create new admin user with unified Firebase/Django integration"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role')
        venue_id = request.POST.get('venue_id', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Validation
        if not all([email, role]):
            return JsonResponse({'error': 'Email and role are required'}, status=400)
        
        if role not in ['siteAdmin', 'venueAdmin', 'subAdmin']:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        if role in ['venueAdmin', 'subAdmin'] and not venue_id:
            return JsonResponse({'error': 'Venue is required for venue admins and sub admins'}, status=400)
        
        if not password or len(password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)
        
        # Validate venue exists
        if venue_id:
            venue = Venue.get_by_id(venue_id)
            if not venue:
                return JsonResponse({'error': 'Selected venue does not exist'}, status=400)
        
        manager = FirebaseAdminManager()
        result = manager.create_admin_user(
            email=email,
            role=role,
            venue_id=venue_id if venue_id else None,
            display_name=display_name if display_name else None,
            password=password
        )
        
        logger.info(f"Site admin {request.user.email} created new {role}: {email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully created {role}: {email}. They can now sign in with their password.',
            'uid': result['uid'],
            'email': result['email']
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return JsonResponse({'error': 'Failed to create admin user'}, status=500)

@login_required
@require_http_methods(["POST"])
def update_admin_user(request):
    """Update admin user role/venue"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        uid = request.POST.get('uid')
        role = request.POST.get('role')
        venue_id = request.POST.get('venue_id', '').strip()
        
        if not all([uid, role]):
            return JsonResponse({'error': 'UID and role are required'}, status=400)
        
        if role not in ['siteAdmin', 'venueAdmin', 'subAdmin']:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        if role in ['venueAdmin', 'subAdmin'] and not venue_id:
            return JsonResponse({'error': 'Venue is required for venue admins and sub admins'}, status=400)
        
        # Validate venue exists
        if venue_id:
            venue = Venue.get_by_id(venue_id)
            if not venue:
                return JsonResponse({'error': 'Selected venue does not exist'}, status=400)
        
        manager = FirebaseAdminManager()
        manager.update_admin_role(
            uid=uid,
            new_role=role,
            new_venue_id=venue_id if venue_id else ''
        )
        
        logger.info(f"Site admin {request.user.email} updated admin {uid} to role {role}")
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated user role to {role}'
        })
        
    except Exception as e:
        logger.error(f"Error updating admin user: {e}")
        return JsonResponse({'error': 'Failed to update admin user'}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_user_status(request):
    """Activate/deactivate admin user"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        uid = request.POST.get('uid')
        action = request.POST.get('action')  # 'activate' or 'deactivate'
        
        if not all([uid, action]):
            return JsonResponse({'error': 'UID and action are required'}, status=400)
        
        if action not in ['activate', 'deactivate']:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        manager = FirebaseAdminManager()
        
        if action == 'deactivate':
            manager.deactivate_admin(uid)
            message = 'Admin user deactivated successfully'
        else:
            manager.activate_admin(uid)
            message = 'Admin user activated successfully'
        
        logger.info(f"Site admin {request.user.email} {action}d admin {uid}")
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error toggling admin status: {e}")
        return JsonResponse({'error': 'Failed to update admin status'}, status=500)

@login_required
@require_http_methods(["POST"])
def delete_admin_user(request):
    """Permanently delete admin user"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        uid = request.POST.get('uid')
        confirm = request.POST.get('confirm')
        
        if not uid:
            return JsonResponse({'error': 'UID is required'}, status=400)
        
        if confirm != 'DELETE':
            return JsonResponse({'error': 'Please type DELETE to confirm'}, status=400)
        
        # Prevent deletion of the current user
        if request.user.email:
            manager = FirebaseAdminManager()
            current_admin = manager.get_admin_by_email(request.user.email)
            if current_admin and current_admin.get('uid') == uid:
                return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
        
        manager.delete_admin(uid)
        
        logger.warning(f"Site admin {request.user.email} deleted admin {uid}")
        
        return JsonResponse({
            'success': True,
            'message': 'Admin user deleted permanently'
        })
        
    except Exception as e:
        logger.error(f"Error deleting admin user: {e}")
        return JsonResponse({'error': 'Failed to delete admin user'}, status=500)

@login_required
@require_http_methods(["POST"])
def send_password_reset(request):
    """Send password reset email to admin user"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        
        manager = FirebaseAdminManager()
        reset_link = manager.send_password_reset(email)
        
        logger.info(f"Site admin {request.user.email} sent password reset to {email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Password reset email sent to {email}',
            'reset_link': reset_link  # In production, you'd email this instead
        })
        
    except Exception as e:
        logger.error(f"Error sending password reset: {e}")
        return JsonResponse({'error': 'Failed to send password reset'}, status=500)
    
    # Add this to users/views.py

import json
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def firebase_login(request):
    """Handle Firebase authentication token"""
    try:
        data = json.loads(request.body)
        id_token = data.get('id_token')
        
        if not id_token:
            return JsonResponse({'error': 'No token provided'}, status=400)
        
        # Authenticate using Firebase token
        from django.contrib.auth import authenticate
        user = authenticate(request, firebase_token=id_token)
        
        if user:
            login(request, user)
            return JsonResponse({
                'success': True,
                'redirect_url': '/',
                'user': {
                    'email': user.email,
                    'display_name': user.display_name,
                    'role': user.role
                }
            })
        else:
            return JsonResponse({'error': 'Authentication failed'}, status=401)
            
    except Exception as e:
        logger.error(f"Firebase login error: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)