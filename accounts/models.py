from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from clients.models import Client
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from core.utils import DEPARTMENT_CHOICES,POSITION_CHOICES



class CustomUser(AbstractUser):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='users', null=True, blank=True)   
    user_department = models.CharField(max_length=100,choices=DEPARTMENT_CHOICES,null=True, blank=True) 
    user_position = models.CharField(max_length=100,choices=POSITION_CHOICES,null=True, blank=True) 
    is_active = models.BooleanField(default=True)

    biometrict_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    ROLE_CHOICES = [
    ('superadmin', 'Super Admin'),   # system-level admin
    ('admin', 'Admin'),              # office admin / HR head 
    ('CEO', 'CEO'),  
    ('CFO', 'CFO'),  
    ('CMO', 'CMO'),  
    ('CTO', 'CTO'),  
    ('director', 'director'),  
    ('general_manager', 'Geberal Manager'),  
    ('manager', 'Manager'),          # department or project manager
    ('team_lead', 'Team Lead'),      # leads a team
    ('employee', 'Employee'),        # general staff
    ('intern', 'Intern'),            # temporary/trainee
    ('hr', 'HR'),                    # human resources
    ('finance', 'Finance'),          # accounts/finance role
    ('it_support', 'IT Support'),    # IT/tech role
    ('guest', 'Guest/User'),         # limited access
]


    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient')   
    email = models.EmailField(blank=True, null=True, unique=False)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)   
    photo_id = models.ImageField(upload_to='user_photo', null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return f"{self.username} - {self.tenant.name if self.tenant else 'No Tenant'}"
    
    

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_profile', null=True, blank=True)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='user_tenants', null=True, blank=True)

    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    

class ActivityLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="activity_logs")
    action = models.CharField(max_length=255)  # e.g. "Visited /employees/add/"
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.timestamp})"

class AllowedEmailDomain(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='allowed_user_email_domains', null=True, blank=True)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='allowed_user_tenant_domains',null=True, blank=True)
    domain = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)  
    updated_on = models.DateTimeField(auto_now=True)  

    class Meta:
        unique_together = ('tenant', 'domain')  

    def __str__(self):
        return f"{self.domain} ({self.tenant.name})"


