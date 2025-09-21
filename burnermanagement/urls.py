# burnermanagement/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def signup_disabled(request):
    """Custom view to disable signup"""
    from django.shortcuts import render
    return render(request, 'account/signup_disabled.html', status=403)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Override signup URL to disable it
    path('accounts/signup/', signup_disabled, name='account_signup'),
    
    # Include all other allauth URLs
    path('accounts/', include('allauth.urls')),
    
    # App URLs
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('venues/', include('venues.urls')),
    path('events/', include('events.urls')),
    path('tickets/', include('tickets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)