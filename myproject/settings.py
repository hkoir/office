

from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-wzlf*t+-g32z73ia4=qdcbq*-2wkw_elwd_^%m3iodhllt9t!1'


DEBUG = True

ALLOWED_HOSTS = ['178.128.95.232','*','dopstech.pro','www.dopstech.pro','localhost']




SHARED_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'django_tenants',  
    'django.contrib.contenttypes',  
    'django.contrib.sessions',     
    'django.contrib.messages',     
    'django.contrib.staticfiles',  
    'django_crontab',               
    'django_celery_beat',   
    'django_extensions',   
    'django.contrib.humanize',   
    'django.contrib.sites',
    'django.contrib.auth',   
    'django.contrib.admin',  
    'accounts',
    'clients',   
    'commonapp',      
    'rest_framework',
    'rest_framework.authtoken',

]

TENANT_APPS = [ 
 
   'logistics',
    'manufacture',
    'product',
    'purchase',
    'sales',
    'supplier',
    'inventory',
    'finance',
    'shipment',
    'reporting',
    'customer',
    'tasks',  
    'core',
    'repairreturn',
    'operations',
    'customerportal',
    'transport',
    'recruitment',
    'officemanagement',
    'leavemanagement'
 
  
    
]


INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

SITE_ID = 1

TENANT_MODEL = "clients.Client"  
TENANT_DOMAIN_MODEL = "clients.Domain"  
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
PUBLIC_SCHEMA_NAME = 'public'

AUTH_USER_MODEL = 'accounts.CustomUser' 


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"



AUTHENTICATION_BACKENDS = [
    'accounts.backends.TenantAuthenticationBackend',  # Custom tenant-aware backend
    'django.contrib.auth.backends.ModelBackend',  # Default Django backend
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.contrib.auth.middleware.AuthenticationMiddleware', 
    'django_tenants.middleware.TenantMiddleware',  
     
    'django.contrib.messages.middleware.MessageMiddleware',  
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
  
       
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]





ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
       'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',               
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_info',           
                'accounts.context_processors.tenant_schema',
                'tasks.context_processors.unread_messages',
                'tasks.context_processors.notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'myproject',  # your PostgreSQL database name
        'USER': 'arafat',      # the user you created for PostgreSQL
        'PASSWORD': 'Arafat_123',  # the password for your PostgreSQL user
        'HOST': 'localhost',    # default for local database
        'PORT': '5432',         # default PostgreSQL port
    }
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }




# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]





import os
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'error.log'),  # Save error logs to this file
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],  # Logs errors to file and console
            'level': 'ERROR',  # Log ERROR level and above
            'propagate': True,
        },
        'commonapp': {  # Replace 'inventory' with your app's name
            'handlers': ['file', 'console'],  # Logs DEBUG and above for this app
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

MAX_PENALTY_CAP = 500.00

CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Use Redis as the broker
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'



LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")


LOGIN_REDIRECT_URL = '/clients/tenant_expire_check/'
LOGIN_URL = 'accounts:login'




EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.your-email-provider.com' 
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@example.com'
# EMAIL_HOST_PASSWORD = 'your-email-password'
# DEFAULT_FROM_EMAIL = 'your-email@example.com'



    

DEFAULT_FROM_EMAIL = 'noreply@ddealshop.com'  # Default sender email
