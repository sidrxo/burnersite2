# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Admin management (site admins only)
    path('admin/', views.admin_management, name='admin_management'),
    path('admin/create/', views.create_admin_user, name='create_admin'),
    path('admin/update/', views.update_admin_user, name='update_admin'),
    path('admin/toggle-status/', views.toggle_user_status, name='toggle_status'),
    path('admin/delete/', views.delete_admin_user, name='delete_admin'),
    path('admin/reset-password/', views.send_password_reset, name='reset_password'),
]