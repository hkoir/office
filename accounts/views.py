import logging
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from django.contrib.sites.shortcuts import get_current_site
from django_tenants.utils import schema_context, get_public_schema_name

from .forms import (
    UserRegistrationForm,
    CustomLoginForm,
    CustomUserCreationForm,
    ProfilePictureForm,
    TenantUserRegistrationForm,
    AssignPermissionsForm,
    UserGroupForm,
    AssignPermissionsToGroupForm,
    PartnerJobSeekerRegistrationForm,
)
from .models import (
    UserProfile,
    CustomUser,
    AllowedEmailDomain,
    ActivityLog,
    PhoneOTP,
)
from .tokens import account_activation_token
from .utils import send_sms
from accounts.backends import TenantAuthenticationBackend

from clients.models import Client, SubscriptionPlan, Subscription, Tenant
from core.models import Employee
from inventory.models import TransferOrder, Warehouse
from logistics.models import PurchaseShipment, SaleShipment
from manufacture.models import MaterialsRequestOrder
from operations.models import OperationsRequestOrder
from product.models import Product, Category
from purchase.models import PurchaseOrder, PurchaseRequestOrder
from sales.models import SaleOrder, SaleRequestOrder
from finance.models import (
    PurchaseInvoice,
    SaleInvoice,
    PurchasePayment,
    SalePayment,
)
from transport.models import Transport
from tasks.models import Ticket, Task

# Initialize logger
logger = logging.getLogger(__name__)



def test_email(request):
    subject = "Test Email from Django Template"
    recipient = "mycpa1973@gmail.com"  # Replace or use request.user.email

    # Render your email template
    html_content = render_to_string('email/test_email.html', {
        'user': request.user,
        'message': "This is a test email rendered from a template."
    })

    email = EmailMultiAlternatives(
        subject,
        "This is the plain text body.",  # fallback
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)

    messages.success(request, "Test email sent successfully!")
    return redirect('clients:tenant_expire_check')  # or wherever you want



def home(request):
    return render(request,'accounts/home.html')


def activity_log_view(request):
    days = int(request.GET.get("days", 7))  
    since = timezone.now() - timedelta(days=days)    
    logs_list = ActivityLog.objects.filter(timestamp__gte=since).order_by('-timestamp')
     
    paginator = Paginator(logs_list, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "accounts/activity_log.html", {
        "page_obj": page_obj,
        "days": days,
    })

def send_tenant_email(email, username, password, subdomain):
    subject = "Your Credentials for login"
    message = (
        f"Welcome to our platform!\n\n"
        f"Your account has been created successfully.\n\n"
        f"Username: {username}\n"
        f"Password: {password}\n"
        f"Subdomain: {subdomain}\n"
        f"Login URL: http://{subdomain}.localhost:8000\n\n"
        f"Thank you for using our service!"
    )
    send_mail(subject, message, 'your-email@example.com', [email])




@login_required
def register_view(request):
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    logger.debug("Current tenant: %s, schema: %s", current_tenant, current_schema)

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        logger.debug("Form submitted with data: %s", request.POST.dict())

        if registerForm.is_valid():
            logger.info("Registration form is valid")
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']

                if role not in ['job-seeker', 'customer']:
                    logger.warning("Invalid role selected: %s", role)
                    registerForm.add_error('role', 'Please select job-seeker or customer User role')
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.role = role
                user.save()
                logger.info("User %s created successfully with role %s", user.username, role)
                if user.phone_number:
                    try:
                        logger.debug("Sending OTP to phone: %s", user.phone_number)
                        request.session['otp_phone'] = user.phone_number
                        send_otp(request, user.phone_number)  
                        logger.info("OTP sent successfully to %s", user.phone_number)
                        if user.email:
                            try:
                                current_site = get_current_site(request)
                                domain = current_site.domain
                                subdomain = f"{current_schema}" if current_schema != 'public' else ''
                                subject = 'Activate your Account'
                                message = render_to_string('accounts/registration/account_activation_email.html', {
                                    'user': user,
                                    'domain': domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': account_activation_token.make_token(user),
                                    'subdomain': subdomain
                                })
                                user.email_user(subject=subject, message=message, fail_silently=True)
                                logger.info("Activation email sent silently to %s", user.email)
                            except Exception as e:
                                logger.warning("Silent email failed for %s: %s", user.email, e, exc_info=True)

                        return redirect('accounts:verify_otp')
                    except Exception as e:
                        logger.error("OTP sending failed for %s: %s", user.phone_number, e, exc_info=True)
                        messages.warning(request, f"SMS failed: {e}")
                if user.email:
                    try:
                        current_site = get_current_site(request)
                        domain = current_site.domain
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        logger.info("Activation email sent to %s", user.email)
                        messages.info(request, "Please check your email to activate your account.")
                        return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
                    except Exception as e:
                        logger.error("Email sending failed for %s: %s", user.email, e, exc_info=True)
                        messages.warning(request, f"Email sending failed: {e}")

                messages.error(request, "Could not send OTP or activation email. Please try again.")
                user.delete()
                logger.warning("User deleted: phone/email sending failed")
                return render(request, 'accounts/registration/register.html', {'form': registerForm})

        else:
            logger.warning("Form invalid: %s", registerForm.errors)

    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
        logger.debug("Rendering empty registration form")

    return render(request, 'accounts/registration/register.html', {'form': registerForm})




@login_required
def register_employee_corporate_user(request):
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    logger.debug("Current tenant: %s, schema: %s", current_tenant, current_schema)

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        logger.debug("Form submitted with data: %s", request.POST.dict())

        if registerForm.is_valid():
            logger.info("Registration form is valid")
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']

                if role in ['job-seeker','customer']:
                    logger.warning("Invalid role selected: %s", role)
                    registerForm.add_error('role', 'Please select Employee or Corporate User role')
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.role = role
                user.save()
                logger.info("User %s created successfully with role %s", user.username, role)

                # Priority 1: Phone OTP
                if user.phone_number:
                    try:
                        logger.debug("Sending OTP to phone: %s", user.phone_number)
                        request.session['otp_phone'] = user.phone_number
                        send_otp(request, user.phone_number)  # send OTP and redirect to verification
                        logger.info("OTP sent successfully to %s", user.phone_number)

                        # Optionally send email silently in the background
                        if user.email:
                            try:
                                current_site = get_current_site(request)
                                domain = current_site.domain
                                subdomain = f"{current_schema}" if current_schema != 'public' else ''
                                subject = 'Activate your Account'
                                message = render_to_string('accounts/registration/account_activation_email.html', {
                                    'user': user,
                                    'domain': domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': account_activation_token.make_token(user),
                                    'subdomain': subdomain
                                })
                                user.email_user(subject=subject, message=message, fail_silently=True)
                                logger.info("Activation email sent silently to %s", user.email)
                            except Exception as e:
                                logger.warning("Silent email failed for %s: %s", user.email, e, exc_info=True)

                        return redirect('accounts:verify_otp')

                    except Exception as e:
                        logger.error("OTP sending failed for %s: %s", user.phone_number, e, exc_info=True)
                        messages.warning(request, f"SMS failed: {e}")

                # Priority 2: Email if phone not provided or OTP failed
                if user.email:
                    try:
                        current_site = get_current_site(request)
                        domain = current_site.domain
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        logger.info("Activation email sent to %s", user.email)
                        messages.info(request, "Please check your email to activate your account.")
                        return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
                    except Exception as e:
                        logger.error("Email sending failed for %s: %s", user.email, e, exc_info=True)
                        messages.warning(request, f"Email sending failed: {e}")

                # If neither phone OTP nor email succeeded
                messages.error(request, "Could not send OTP or activation email. Please try again.")
                user.delete()
                logger.warning("User deleted: phone/email sending failed")
                return render(request, 'accounts/registration/register.html', {'form': registerForm})

        else:
            logger.warning("Form invalid: %s", registerForm.errors)

    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
        logger.debug("Rendering empty registration form")

    return render(request, 'accounts/registration/register.html', {'form': registerForm})






@login_required
def register_corporate_user_only(request): 
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    logger.debug("Current tenant: %s, schema: %s", current_tenant, current_schema)

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        logger.debug("Form submitted with data: %s", request.POST.dict())

        if registerForm.is_valid():
            logger.info("Registration form is valid")
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']

                if not role == 'corporate-user':
                    logger.warning("Invalid role selected: %s", role)
                    registerForm.add_error('role', 'Please select Corporate User role')
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.role = role
                user.save()
                logger.info("User %s created successfully with role %s", user.username, role)

                # Priority 1: Phone OTP
                if user.phone_number:
                    try:
                        logger.debug("Sending OTP to phone: %s", user.phone_number)
                        request.session['otp_phone'] = user.phone_number
                        send_otp(request, user.phone_number)  # send OTP and redirect to verification
                        logger.info("OTP sent successfully to %s", user.phone_number)

                        # Optionally send email silently in the background
                        if user.email:
                            try:
                                current_site = get_current_site(request)
                                domain = current_site.domain
                                subdomain = f"{current_schema}" if current_schema != 'public' else ''
                                subject = 'Activate your Account'
                                message = render_to_string('accounts/registration/account_activation_email.html', {
                                    'user': user,
                                    'domain': domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': account_activation_token.make_token(user),
                                    'subdomain': subdomain
                                })
                                user.email_user(subject=subject, message=message, fail_silently=True)
                                logger.info("Activation email sent silently to %s", user.email)
                            except Exception as e:
                                logger.warning("Silent email failed for %s: %s", user.email, e, exc_info=True)

                        return redirect('accounts:verify_otp')

                    except Exception as e:
                        logger.error("OTP sending failed for %s: %s", user.phone_number, e, exc_info=True)
                        messages.warning(request, f"SMS failed: {e}")

                # Priority 2: Email if phone not provided or OTP failed
                if user.email:
                    try:
                        current_site = get_current_site(request)
                        domain = current_site.domain
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        logger.info("Activation email sent to %s", user.email)
                        messages.info(request, "Please check your email to activate your account.")
                        return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
                    except Exception as e:
                        logger.error("Email sending failed for %s: %s", user.email, e, exc_info=True)
                        messages.warning(request, f"Email sending failed: {e}")

                # If neither phone OTP nor email succeeded
                messages.error(request, "Could not send OTP or activation email. Please try again.")
                user.delete()
                logger.warning("User deleted: phone/email sending failed")
                return render(request, 'accounts/registration/register.html', {'form': registerForm})

        else:
            logger.warning("Form invalid: %s", registerForm.errors)

    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
        logger.debug("Rendering empty registration form")

    return render(request, 'accounts/registration/register.html', {'form': registerForm})


def register_public(request):   
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data.get('role')

                # Optional: enforce roles for public registration
                if role not in ['job-seeker', 'customer']:
                    registerForm.add_error('role', 'Please select Job-Seeker or Customer role')
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.role = role
                user.save()

                # Priority 1: Phone OTP
                if user.phone_number:
                    try:
                        request.session['otp_phone'] = user.phone_number
                        send_otp(request, user.phone_number)  # send OTP and redirect to verification

                        # Optional silent email
                        if user.email:
                            try:
                                current_site = get_current_site(request)
                                domain = current_site.domain
                                subdomain = '' if current_schema == 'public' else current_schema
                                subject = 'Activate your Account'
                                message = render_to_string('accounts/registration/account_activation_email.html', {
                                    'user': user,
                                    'domain': domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': account_activation_token.make_token(user),
                                    'subdomain': subdomain
                                })
                                user.email_user(subject=subject, message=message, fail_silently=True)
                            except Exception:
                                pass  # silent fail

                        return redirect('accounts:verify_otp')

                    except Exception as e:
                        messages.warning(request, f"SMS failed: {e}")

                # Priority 2: Email activation if no phone or OTP failed
                if user.email:
                    try:
                        current_site = get_current_site(request)
                        domain = current_site.domain
                        subdomain = '' if current_schema == 'public' else current_schema
                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        messages.info(request, "Please check your email to activate your account.")
                        return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
                    except Exception as e:
                        messages.warning(request, f"Email sending failed: {e}")

                # If neither phone nor email succeeded
                messages.error(request, "Could not send OTP or activation email. Please try again.")
                user.delete()
                return render(request, 'accounts/registration/register.html', {'form': registerForm})

        else:
            messages.error(request, "Form contains errors. Please correct and try again.")

    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)

    return render(request, 'accounts/registration/register.html', {'form': registerForm})




def register_partner_job_seeker(request):   
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    logger.debug("Current tenant: %s, schema: %s", current_tenant, current_schema)

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        logger.debug("Form submitted with data: %s", request.POST.dict())

        if registerForm.is_valid():
            logger.info("Registration form is valid")
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']

                if role not in ['job-seeker', 'customer']:
                    logger.warning("Invalid role selected: %s", role)
                    registerForm.add_error('role', 'Please select Corporate User role')
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.role = role
                user.save()
                logger.info("User %s created successfully with role %s", user.username, role)

                # Priority 1: Phone OTP
                if user.phone_number:
                    try:
                        logger.debug("Sending OTP to phone: %s", user.phone_number)
                        request.session['otp_phone'] = user.phone_number
                        send_otp(request, user.phone_number)  # send OTP and redirect to verification
                        logger.info("OTP sent successfully to %s", user.phone_number)

                        # Optionally send email silently in the background
                        if user.email:
                            try:
                                current_site = get_current_site(request)
                                domain = current_site.domain
                                subdomain = f"{current_schema}" if current_schema != 'public' else ''
                                subject = 'Activate your Account'
                                message = render_to_string('accounts/registration/account_activation_email.html', {
                                    'user': user,
                                    'domain': domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': account_activation_token.make_token(user),
                                    'subdomain': subdomain
                                })
                                user.email_user(subject=subject, message=message, fail_silently=True)
                                logger.info("Activation email sent silently to %s", user.email)
                            except Exception as e:
                                logger.warning("Silent email failed for %s: %s", user.email, e, exc_info=True)

                        return redirect('accounts:verify_otp')

                    except Exception as e:
                        logger.error("OTP sending failed for %s: %s", user.phone_number, e, exc_info=True)
                        messages.warning(request, f"SMS failed: {e}")

                # Priority 2: Email if phone not provided or OTP failed
                if user.email:
                    try:
                        current_site = get_current_site(request)
                        domain = current_site.domain
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        logger.info("Activation email sent to %s", user.email)
                        messages.info(request, "Please check your email to activate your account.")
                        return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
                    except Exception as e:
                        logger.error("Email sending failed for %s: %s", user.email, e, exc_info=True)
                        messages.warning(request, f"Email sending failed: {e}")

                # If neither phone OTP nor email succeeded
                messages.error(request, "Could not send OTP or activation email. Please try again.")
                user.delete()
                logger.warning("User deleted: phone/email sending failed")
                return render(request, 'accounts/registration/register.html', {'form': registerForm})

        else:
            logger.warning("Form invalid: %s", registerForm.errors)

    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
        logger.debug("Rendering empty registration form")

    return render(request, 'accounts/registration/register.html', {'form': registerForm})




def account_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        tenant_schema = getattr(user.tenant, "schema_name", None)

        if tenant_schema == "public":
            user.is_active = True
            user.is_staff = False
        elif user.role == 'employee':
            user.is_active = True
            user.is_staff = True
        else:
            user.is_active = True
            user.is_staff = False

        user.save()   
        login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
        messages.success(request, "Your account has been activated! You can work now.")
        return redirect('clients:tenant_expire_check')
    return render(request, 'accounts/registration/activation_invalid.html')



################################## otp verification for registration ########################
def send_otp(request, phone_number):
    if not phone_number:
        return render(request, "accounts/registration/register.html", {"error": "Phone number required."})


    user = get_object_or_404(CustomUser,phone_number = phone_number)
    otp_obj, _ = PhoneOTP.objects.get_or_create(user=user)
    otp_obj.generate_otp()

    message = f"Your verification code is: {otp_obj.otp}"
    try:
        send_sms(tenant=getattr(request, "tenant", None), phone_number=phone_number, message=message)
        print(f'your otp code is {otp_obj.otp}')
    except Exception as e:
        return render(request, "accounts/registration/register.html", {"error": f"SMS failed: {e}"})

    return render(request, "accounts/verify_otp.html", {
        "phone": phone_number,
        "valid_until": otp_obj.valid_until,
    })


def verify_otp(request):
    current_tenant = getattr(connection, 'tenant', None)
    logger.debug("Current tenant: %s", current_tenant)
    phone = request.session.get('otp_phone')
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        phone = request.POST.get('phone', phone)
        logger.debug("Verifying OTP for phone: %s, input OTP: %s", phone, otp_input)

        if not phone or not otp_input:
            messages.error(request, "Phone number and OTP are required.")
            return render(request, "accounts/verify_otp.html", {"phone": phone})

        user = get_object_or_404(CustomUser,phone_number = phone)
        otp_entry = PhoneOTP.objects.filter(user=user).order_by('-created_at').first()
        if not otp_entry:
            messages.error(request, "OTP not found. Please request a new one.")
            logger.warning("No OTP entry found for phone: %s", phone)
            return render(request, "accounts/verify_otp.html", {"phone": phone})
        if constant_time_compare(str(otp_entry.otp), str(otp_input)) and timezone.now() <= otp_entry.valid_until:
            otp_entry.is_verified = True
            otp_entry.save()
            logger.info("OTP verified successfully for phone: %s", phone)  
            user = CustomUser.objects.filter(phone_number=phone).first()
            if user:
                user.is_phone_verified = True
                user.is_active = True
                if current_tenant:
                    user.tenant = current_tenant
                if user.role == 'employee':
                    user.staff = True
                else:
                    user.staff = False
                user.save()
                logger.info("User %s activated via OTP", user.username)
                login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
                messages.success(request, "Phone number verified successfully. You are now logged in.")
                # Clear OTP session
                request.session.pop('otp_phone', None)
                return redirect("clients:tenant_expire_check")
            else:
                messages.error(request, "No user found for this phone number.")
                logger.warning("No user found for phone: %s", phone)
                return render(request, "accounts/verify_otp.html", {"phone": phone})
        else:
            messages.error(request, "Invalid or expired OTP.")
            logger.warning("OTP failed for phone: %s", phone)
            return render(request, "accounts/verify_otp.html", {"phone": phone})
    logger.debug("Rendering OTP form for phone: %s", phone)
    if not phone:
        messages.error(request, "Phone number not found in session. Please register first.")
        return redirect("accounts:register")
    return render(request, "accounts/verify_otp.html", {"phone": phone})


###################################### Password reset ########################################
def send_password_reset_otp(request,phone_number=None):
    valid_until=None
    if request.method == "POST":
        phone_number = request.POST.get("phone")
        if not phone_number:
            messages.error(request, "Phone number is required.")
            return redirect("accounts:forgot_password")
        user = get_object_or_404(CustomUser, phone_number=phone_number)
        PhoneOTP.objects.filter(user=user, purpose='forgot_password').delete()
        otp_obj = PhoneOTP.objects.create(user=user, purpose='forgot_password')
        valid_until = otp_obj.valid_until
        otp_obj.generate_otp()
        message = f"Your verification code is: {otp_obj.otp}"
        try:
            send_sms(tenant=getattr(request, "tenant", None), phone_number=phone_number, message=message)
            print(f'OTP sent: {otp_obj.otp}')
        except Exception as e:
            messages.error(request, f"SMS sending failed: {e}")
            return redirect("accounts:forgot_password")
        request.session['reset_phone_number'] = phone_number
        messages.info(request, "OTP sent. Please enter OTP and new password below.")
        return redirect("accounts:verify_password_reset_otp")  
    return render(request, "accounts/forgot_password.html",
        {
        "phone": phone_number,
        "valid_until":valid_until,
        })



def verify_password_reset_otp(request):
    phone = request.session.get("reset_phone_number")
    if not phone:
        messages.error(request, "No phone number found. Please request a new OTP.")
        return redirect("accounts:forgot_password")

    user = get_object_or_404(CustomUser, phone_number=phone)
    otp_entry = PhoneOTP.objects.filter(user=user, purpose='forgot_password').order_by('-created_at').first()

    if request.method == "POST":
        otp_input = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        if not otp_input or not new_password or not confirm_password:
            return render(request, "accounts/reset_password_form.html",
                          {"error": "All fields are required.", "phone": phone, "valid_until": otp_entry.valid_until if otp_entry else None})

        if not otp_entry:
            return render(request, "accounts/reset_password_form.html",
                          {"error": "OTP not found. Please request a new OTP.", "phone": phone})

        if not (constant_time_compare(str(otp_entry.otp), str(otp_input)) and timezone.now() <= otp_entry.valid_until):
            return render(request, "accounts/reset_password_form.html",
                          {"error": "Invalid or expired OTP.", "phone": phone, "valid_until": otp_entry.valid_until})

        if new_password != confirm_password:
            return render(request, "accounts/reset_password_form.html",
                          {"error": "Passwords do not match.", "phone": phone, "valid_until": otp_entry.valid_until})

        user.set_password(new_password)
        user.is_active = True
        user.is_phone_verified = True
        user.save()
        otp_entry.is_verified = True
        otp_entry.save()
        request.session.pop("reset_phone_number", None)
        login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
        messages.success(request, "Your password was successfully changed.")
        return redirect("clients:tenant_expire_check")
    return render(request, "accounts/reset_password_form.html", {
        "phone": phone,
        "valid_until": otp_entry.valid_until if otp_entry else None
    })

################################### Password Change ############################################

@login_required
def send_change_password_otp(request,phone_number=None):
    valid_until =None
    if request.method == "POST":       
        PhoneOTP.objects.filter(user=request.user, purpose="change_password").delete()
        otp_obj = PhoneOTP.objects.create(user=request.user, purpose="change_password")
        otp_obj.generate_otp()
        valid_until: otp_obj.valid_until
        message = f"Your OTP to change password is: {otp_obj.otp}"
        try:
            send_sms(
                tenant=getattr(request, "tenant", None),
                phone_number=request.user.phone_number,
                message=message,
            )
            print(f"Password change OTP sent: {otp_obj.otp}")
        except Exception as e:
            messages.error(request, f"Failed to send SMS: {e}")
            return redirect("accounts:send_change_password_otp")
        messages.success(request, "OTP sent to your phone. Please enter it below to change your password.")
        return redirect("accounts:verify_change_password_otp")
    return render(request, "accounts/send_change_password_otp.html",
                {
                    "phone": phone_number,
                    "valid_until": valid_until,
                })



@login_required
def verify_change_password_otp(request):
    if request.method == "POST":
        phone = request.user.phone_number
        otp_input = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validate inputs
        if not all([otp_input, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect("accounts:verify_change_password_otp")

        # Fetch latest OTP entry
        otp_entry = PhoneOTP.objects.filter(
            user=request.user,
            purpose="change_password",
            is_verified=False
        ).order_by("-created_at").first()

        if not otp_entry:
            messages.error(request, "No OTP found. Please request a new one.")
            return redirect("accounts:send_change_password_otp")

        # Verify OTP and expiry
        if not (constant_time_compare(str(otp_entry.otp), str(otp_input)) and timezone.now() <= otp_entry.valid_until):
            messages.error(request, "Invalid or expired OTP.")
            return redirect("accounts:verify_change_password_otp")

        # Check password match
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("accounts:verify_change_password_otp")

        # Update password
        user = request.user
        user.set_password(new_password)
        user.save()

        otp_entry.is_verified = True
        otp_entry.save()

        messages.success(request, "Your password has been changed successfully! Please log in again.")
        return redirect("accounts:login")
    return render(request, "accounts/verify_change_password_otp.html")

#################################################################################################


@login_required
def update_profile_picture(request): 
    if not request.user.is_authenticated:
        return redirect('core:home') 

    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    profile_picture_url = user_profile.profile_picture.url if user_profile.profile_picture else None
    user_info = request.user.get_full_name() or request.user.username

    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            if request.user.groups.filter(name__in=('Customer','public','job_seekers')).exists():
                return redirect('clients:dashboard')  
            else:
                messages.success(request, "Login successful!")
                return redirect('core:dashboard')    
        else:
            messages.error(request,'there is an error in form')   
            print(form.errors)    
    else:
        form = ProfilePictureForm(instance=user_profile)

    return render(
        request, 
        'accounts/change_profile_picture.html', 
        {'form': form, 'user_info': user_info, 'profile_picture_url': profile_picture_url}
    )




def login_view(request):
    current_tenant = None
    if hasattr(connection, 'tenant'):
        current_tenant = connection.tenant         
        current_schema = current_tenant.schema_name   

        subscriptions = Subscription.objects.all()
        current_date = timezone.now().date()
        for subscription in subscriptions:
            if subscription.expiration_date:
                if subscription.expiration_date > current_date:
                    subscription.is_expired = True
                    subscription.save()
    form = CustomLoginForm(initial={'tenant': current_schema })   

    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
                    
            user = authenticate(request, username=username, password=password)
            tenant = current_schema 
            if user:                  
                login(request, user,backend='accounts.backends.TenantAuthenticationBackend')
                current_schema_found=request.tenant.schema_name == get_public_schema_name()
                if not current_schema_found:   
                    messages.success(request, "Login successful!")                      
                    tenant_url = f"http://{tenant}.dopstech.pro/clients/tenant_expire_check/"
                    return redirect(tenant_url)       
                else:
                    messages.success(request,"login successful!")                      
                    tenant_url = f"http://dopstech.pro/clients/tenant_expire_check/"
                    return redirect(tenant_url)     

            else:
                messages.error(request, "Invalid username or password.")
        else:
            print(form.errors)
            form = CustomLoginForm(initial={'tenant':  current_schema })  
            messages.error(request, "Please provide correct username and password")
  
    
    form = CustomLoginForm(initial={'tenant':  current_schema })    
    return render(request, 'accounts/registration/login.html', {'form': form})





def logged_out_view(request):
    plans = SubscriptionPlan.objects.all().order_by('duration')
    for plan in plans:
        plan.features_list = plan.features.split(',')
        
    is_partner_job_seeker = False    
    is_public = False

    if request.user.is_authenticated:        
        is_partner_job_seeker = request.user.groups.filter(name__in=('partner','job_seeker')).exists()       
        is_public = request.user.groups.filter(name='public').exists()
       
    logout(request)  
   
    return render(request, 'accounts/registration/logged_out.html',{'plans':plans})



def assign_model_permission_to_user(user, model_name, permission_codename): 
    try:
        app_label, model_label = model_name.split('.')
        model = apps.get_model(app_label, model_label)
        content_type = ContentType.objects.get_for_model(model)
        permission = Permission.objects.get(codename=permission_codename, content_type=content_type)

        user.user_permissions.add(permission)
        user.save()
        
        return f"Permission '{permission_codename}' successfully assigned to {user.username}."
    except Permission.DoesNotExist:
        return f"Permission '{permission_codename}' does not exist for the model '{model_name}'."
    except Exception as e:
        return f"An error occurred: {e}"



@login_required
def assign_permissions(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to assign roles.")
        return redirect('core:home')

    if request.method == 'POST':
        form = AssignPermissionsForm(request.POST)
        if form.is_valid():
            try:
               
                selected_permissions = form.cleaned_data['permissions']
                model_name = form.cleaned_data['model_name']   
                email = form.cleaned_data['email']  
                user = CustomUser.objects.get(email=email)
                     

                cleaned_model_name = model_name.strip("[]").strip("'\"")
                
                user = CustomUser.objects.get(email=email)
                
                for permission_codename in selected_permissions:
                    cleaned_codename = permission_codename.strip("[]").strip("'\"")                    

                    message = assign_model_permission_to_user(user, cleaned_model_name, cleaned_codename)
                    messages.success(request, message)
                
                return redirect('accounts:assign_permissions')
            except Permission.DoesNotExist:
                messages.error(request, f"Permission '{permission_codename}' does not exist.")
            except Exception as e:
                print(e)
                messages.error(request, f"An error occurred: {e}")
        else:
            print(form.errors)
    else:
        form = AssignPermissionsForm()

    users = CustomUser.objects.all().order_by('-date_joined')
    paginator = Paginator(users,8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/assign_permission.html', {'form': form, 'users': users,'page_obj':page_obj})



@login_required
def assign_user_to_group(request):
    group_data = Group.objects.all()

    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email'] 
            group = form.cleaned_data['group']
            new_group_name = form.cleaned_data['new_group_name']

            try:
                user = CustomUser.objects.get( email=email)
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' does not exist.")
                return redirect('accounts:assign_user_to_group')

            if group:
                user.groups.add(group)
                messages.success(request, f"User '{email}' was added to the existing group '{group.name}'.")
            elif new_group_name:
                group, created = Group.objects.get_or_create(name=new_group_name)
                user.groups.add(group)
                if created:
                    messages.success(request, f"Group '{new_group_name}' was created and '{username}' was added to it.")
                else:
                    messages.success(request, f"User '{username}' was added to the existing group '{new_group_name}'.")
            
            user.save()
            return redirect('accounts:assign_user_to_group')
    else:
        form = UserGroupForm()
    return render(request, 'accounts/assign_user_to_group.html', {'form': form,'group_data':group_data})




def assign_permissions_to_group(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to assign roles.")
        return redirect('core:home')

    group_name = None
    assigned_permissions = []
    group_data = Group.objects.all() 

    if request.method == 'POST':
        form = AssignPermissionsToGroupForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            model_name = form.cleaned_data['model_name']
            selected_permissions = form.cleaned_data['permissions']

            try:
                model_class = apps.get_model(*model_name.split('.'))
                content_type = ContentType.objects.get_for_model(model_class)

                for permission in selected_permissions:
                    if permission.content_type == content_type:
                        group.permissions.add(permission)

                group_name = group.name
                assigned_permissions = group.permissions.select_related('content_type').all() 
                messages.success(request, f"Permissions successfully assigned to the group '{group.name}'.")
                return redirect('accounts:assign_permissions_to_group')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
        else:
            print(form.errors)
    else:
        form = AssignPermissionsToGroupForm()

    groups_info = []
    for group in group_data:
        users_in_group = group.user_set.all() 
        permissions_in_group = group.permissions.select_related('content_type').all()  
        groups_info.append({
            'group': group,
            'users': users_in_group,
            'permissions': permissions_in_group
        })

    return render(
        request,
        'accounts/assign_permissions_to_group.html',
        {
            'form': form,
            'group_name': group_name,
            'assigned_permissions': assigned_permissions,
            'groups_info': groups_info,  # Pass the group data to the template
        }
    )



# for ajax
def get_permissions_for_model(request):
    model_name = request.GET.get('model_name', '')    
    try:
        app_label, model_name = model_name.split('.')
        model_class = apps.get_model(app_label, model_name)   
        content_type = ContentType.objects.get_for_model(model_class) 
        permissions = Permission.objects.filter(content_type=content_type)
        permission_data = [
            {'id': perm.id, 'name': perm.name, 'codename': perm.codename}
            for perm in permissions
        ]        
        return JsonResponse({'permissions': permission_data})    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




def common_search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(product_id__icontains=query)
        ).values('id', 'name', 'product_id')
        results.extend([
            {'id': prod['id'], 'text': f"{prod['name']} ({prod['product_id']})"}
            for prod in products
        ])

        categories = Category.objects.filter(
            Q(name__icontains=query) | Q(category_id__icontains=query)
        ).values('id', 'name', 'category_id')
        results.extend([
            {'id': prod['id'], 'text': f"{prod['name']} ({prod['category_id']})"}
            for prod in categories
        ])

        employees = Employee.objects.filter(
            Q(name__icontains=query) | Q(employee_code__icontains=query)
        ).values('id', 'name', 'employee_code')
        results.extend([
            {'id': emp['id'], 'text': f"{emp['name']} ({emp['employee_code']})"}
            for emp in employees
        ])   

        purchase_orders = PurchaseOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in purchase_orders
        ])   

        purchase_request_orders = PurchaseRequestOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in purchase_request_orders
        ])   

        
        purchase_shipment_orders = PurchaseShipment.objects.filter(
            Q(shipment_id__icontains=query)
        ).values('id', 'shipment_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['shipment_id']}"}
            for data in purchase_shipment_orders
        ])       


        purchase_invoice_numbers = PurchaseInvoice.objects.filter(
            Q(invoice_number__icontains=query)
        ).values('id', 'invoice_number')
        results.extend([
            {'id': data['id'], 'text': f"{data['invoice_number']}"}
            for data in purchase_invoice_numbers
        ])  


        sale_orders = SaleOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in sale_orders
        ])   

        sale_request_orders = SaleRequestOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in sale_request_orders
        ])        


        sale_shipment_orders = SaleShipment.objects.filter(
            Q(shipment_id__icontains=query)
        ).values('id', 'shipment_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['shipment_id']}"}
            for data in sale_shipment_orders
        ])       


        sale_invoice_numbers = SaleInvoice.objects.filter(
            Q(invoice_number__icontains=query)
        ).values('id', 'invoice_number')
        results.extend([
            {'id': data['id'], 'text': f"{data['invoice_number']}"}
            for data in sale_invoice_numbers
        ])   

        transfer_id = TransferOrder.objects.filter(
            Q(order_number__icontains=query)
        ).values('id', 'order_number')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_number']}"}
            for data in transfer_id
        ]) 
    
        materials_orders = MaterialsRequestOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in materials_orders
        ]) 

        operations_orders = OperationsRequestOrder.objects.filter(
            Q(order_id__icontains=query)
        ).values('id', 'order_id')
        results.extend([
            {'id': data['id'], 'text': f"{data['order_id']}"}
            for data in operations_orders
        ]) 

        vehicle = Transport.objects.filter(
            Q(vehicle_registration_number__icontains=query)
        ).values('id', 'vehicle_registration_number')
        results.extend([
            {'id': data['id'], 'text': f"{data['vehicle_registration_number']}"}
            for data in vehicle
        ]) 

    return JsonResponse({'results': results})



@login_required
def search_all(request):
    query = request.GET.get('q')
   
    employees = Employee.objects.filter(
        Q(name__icontains=query) | 
        Q(employee_code__icontains=query) | 
        Q(email__icontains=query) | 
        Q(phone__icontains=query) | 
        Q(position__name__icontains=query) | 
        Q(department__name__icontains=query)
    )

    products = Product.objects.filter(
        Q(name__icontains=query)         
    )
    tickets = Ticket.objects.filter(
        Q(ticket_id__icontains=query)         
    )

    tasks = Task.objects.filter(
        Q(task_id__icontains=query)         
    )



    return render(request, 'accounts/search_results.html', {
        'employees': employees, 
        'products':products,
        'tickets':tickets,
        'tasks':tasks,
        'query': query,
        
    })
