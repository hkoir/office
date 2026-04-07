from django.db import connection
from django_tenants.utils import get_public_schema_name

from .models import UserProfile
from tasks.models import TaskMessage
from core.models import Company


def user_info(request):
    profile_picture_url = None
    organization_name = None 
  
    if connection.schema_name != get_public_schema_name():
        organization_name = Company.objects.first()

    if request.user.is_authenticated: 
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile and user_profile.profile_picture:
            profile_picture_url = user_profile.profile_picture.url

    return {
        'user_info': request.user.username if request.user.is_authenticated else None,
        'profile_picture_url': profile_picture_url,
        'organization_name': organization_name,
    }


def tenant_schema(request):
    schema_name = getattr(request.tenant, 'schema_name', 'public')
    return {'schema_name': schema_name}





