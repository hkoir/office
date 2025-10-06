from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model
from django.core.exceptions import PermissionDenied
from clients.models import Client
User = get_user_model()       
UserModel = get_user_model()

class TenantAuthenticationBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None

        if username is None or password is None:
            return None

        try:
            # Try phone number first
            user = UserModel.objects.get(phone_number=username)
        except UserModel.DoesNotExist:
            try:
                # Then try email
                user = UserModel.objects.get(email=username)
            except UserModel.DoesNotExist:
                try:
                    # Then try username
                    user = UserModel.objects.get(username=username)
                except UserModel.DoesNotExist:
                    return None

        if user and user.check_password(password):
            return user

        return None

        
