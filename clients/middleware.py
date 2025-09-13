from django.shortcuts import redirect
from django_tenants.utils import get_tenant_model
from django.http import Http404
import logging

logger = logging.getLogger(__name__)
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from django.contrib import messages

from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.http import HttpResponseForbidden
from django.urls import resolve
from django.contrib.auth import logout
from django.conf import settings
from django.utils.timezone import now
from.models import UserRequestLog
from django.urls import Resolver404


from django.contrib.auth import get_user_model
from accounts.models import UserProfile  
User = get_user_model() 

from accounts.models import ActivityLog


class CustomTenantAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant = getattr(request, 'tenant', None)
        schema_name = getattr(connection, 'schema_name', None)
        is_public_tenant = tenant and tenant.schema_name == get_public_schema_name()

        if schema_name:
            request.session.cookie_name = f'sessionid_{schema_name}'

        user = request.user
   
        if is_public_tenant:
            if user.is_authenticated:
                logout(request)
                request.session.flush()
            return 

        if user.is_authenticated and tenant:
            user_tenant = getattr(user, 'tenant', None)

            if user.is_superuser:
                return

            if not user_tenant or user_tenant.schema_name != tenant.schema_name:
                logout(request)
                request.session.flush()
                messages.error(request, "You are not allowed to log in to this tenant.")

                if user_tenant:
                    return redirect(f'https://www.{user_tenant.schema_name}.dopstech.pro')
                return redirect('https://www.dopstech.pro')




class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            path = request.path

            # skip logging for activity log itself, admin, static/media
            skip_paths = [
                "/activity-log",
                "/admin",
                "/static",
                "/media",
            ]

            if not any(path.startswith(p) for p in skip_paths):
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Visited {path}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

        return response

