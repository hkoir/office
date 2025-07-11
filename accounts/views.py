
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse,JsonResponse
from django.db.models import Q

from .forms import UserRegistrationForm,CustomLoginForm,CustomUserCreationForm,ProfilePictureForm
from.models import UserProfile

from inventory.models import TransferOrder,Warehouse
from product.models import Product,Category
from core.models import Employee
from purchase.models import PurchaseOrder,PurchaseRequestOrder
from logistics.models import PurchaseShipment,SaleShipment
from finance.models import PurchaseInvoice,SaleInvoice,PurchasePayment,SalePayment
from sales.models import SaleOrder,SaleRequestOrder
from manufacture.models import MaterialsRequestOrder
from operations.models import OperationsRequestOrder

from django.db import connection
from .forms import TenantUserRegistrationForm

from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.db import transaction
from clients.models import Client,SubscriptionPlan

from .forms import AssignPermissionsForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from django.apps import apps
from django.http import JsonResponse
from django.contrib.auth.models import User, Group
from .forms import UserGroupForm
from .forms import AssignPermissionsToGroupForm
from django.core.paginator import Paginator
from transport.models import Transport
from django.contrib.auth.models import Group
from tasks.models import Ticket,Task
from django_tenants.utils import schema_context

from .tokens import account_activation_token
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from.models import CustomUser
from django.core.mail import send_mail

from.forms import PartnerJobSeekerRegistrationForm

from clients.models import Subscription
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from.models import AllowedEmailDomain 
from clients.models import Tenant



def home(request):
    return render(request,'accounts/home.html')


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




def register_view(request):   
    current_tenant = None
    current_schema = None

    if hasattr(connection, 'tenant') and connection.tenant:
        current_tenant = connection.tenant
        current_schema = connection.tenant.schema_name   

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)

        if registerForm.is_valid():
            with transaction.atomic():  
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data['email']
                email_domain = user.email.split('@')[-1] if '@' in user.email else ''
                user.set_password(registerForm.cleaned_data['password1'])

                if CustomUser.objects.filter(email=user.email).exists():
                    messages.error(request, "This email is already registered.")
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                user.is_active = False
                user.tenant = current_tenant
                user.save()

                current_site = get_current_site(request)
                subdomain = current_schema if current_schema != 'public' else ''
                domain = current_site.domain  # e.g., "localhost"

                subject = 'Activate your Account'
                message = render_to_string('accounts/registration/account_activation_email.html', {
                    'user': user,
                    'domain': domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                    'subdomain': subdomain
                })
                user.email_user(subject=subject, message=message)

                tenant_instance = Client.objects.filter(schema_name=current_tenant.schema_name).first() if current_tenant else None
                UserProfile.objects.create(
                    user=user,
                    tenant=tenant_instance,
                    profile_picture=registerForm.cleaned_data.get('profile_picture'),
                )

                messages.info(request, "Please check your email to activate your account.")
                return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})  
    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)    
    return render(request, 'accounts/registration/register.html', {'form': registerForm})


def register_public(request):   
    current_tenant = None
    if hasattr(connection, 'tenant'):      
        current_schema = connection.tenant.schema_name   
        current_tenant = connection.tenant         
    
    if request.method == 'POST':
        registerForm= TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data['email']
                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.save()

                current_site = get_current_site(request)
               
                if connection.tenant.schema_name == 'public':
                    subdomain = ''  # Empty for public domain
                    domain = current_site.domain  # e.g., "localhost"
                else:
                    subdomain = connection.tenant.schema_name  # e.g., "demo1"
                    domain = current_site.domain  # e.g., "localhost"
                subject = 'Activate your Account'
                message = render_to_string('accounts/registration/account_activation_email.html', {
                    'user': user,
                    'domain': domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                    'subdomain':subdomain
                })
                user.email_user(subject=subject, message=message)
                user_profile = UserProfile.objects.create(
                    user=user,
                    tenant=Client.objects.filter(schema_name=current_tenant.schema_name).first(),  # Ensuring correct lookup
                    profile_picture=registerForm.cleaned_data.get('profile_picture'),
                )
                user_profile.save()

            return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
    return render(request, 'accounts/registration/register.html', {'form': registerForm})





def register_partner_job_seeker(request):   
    current_tenant = None    
    if hasattr(connection, 'tenant'):       
        current_tenant_schema = connection.tenant.schema_name   
        current_tenant = request.tenant  #current_tenant = request.user.tenant # from model     

    registerForm=  PartnerJobSeekerRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
    
    if request.method == 'POST':
        registerForm=  PartnerJobSeekerRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data['email']
                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.save()

                user_type = registerForm.cleaned_data['user_type']
                if user_type == 'register-as_business-parner':
                    partner_group, created = Group.objects.get_or_create(name='partner')
                    user.groups.add(partner_group)

                elif user_type == 'register-as-job-seeker':
                    job_seeker_group, created = Group.objects.get_or_create(name='job_seeker')
                    user.groups.add(job_seeker_group)

                current_site = get_current_site(request)
               
                if connection.tenant.schema_name == 'public':
                    subdomain = ''  # Empty for public domain
                    domain = current_site.domain  # e.g., "localhost"
                else:
                    subdomain = connection.tenant.schema_name  # e.g., "demo1"
                    domain = current_site.domain  # e.g., "localhost"
                subject = 'Activate your Account'
                message = render_to_string('accounts/registration/account_activation_email.html', {
                    'user': user,
                    'domain': domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                    'subdomain':subdomain
                })
                user.email_user(subject=subject, message=message)
                UserProfile.objects.create(
                        user=user,
                        tenant=Client.objects.filter(schema_name=current_tenant).first(),
                        profile_picture=registerForm.cleaned_data.get('profile_picture'),
                    )
            return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
    else:
        registerForm = PartnerJobSeekerRegistrationForm(tenant=current_tenant)
    return render(request, 'accounts/registration/register.html', {'form': registerForm})


def account_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)  
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None  

    if user and account_activation_token.check_token(user, token):

        if user.tenant.schema_name == "public":
            user.is_active = True
            user.is_staff = False  
            user.save()
            messages.success(request, "Your account has been activated! You can work now.")
            login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
            return redirect('clients:tenant_expire_check')

        email_domain = user.email.split('@')[-1]      
        allowed_domains = AllowedEmailDomain.objects.filter(tenant=user.tenant).values_list('domain', flat=True)

        if not allowed_domains:
            tenant_owner = Tenant.objects.filter(tenant=user.tenant).first()
            tenant_owner_email = tenant_owner.email if tenant_owner else ''

            tenant_owner_domain = tenant_owner_email.split('@')[-1] if tenant_owner_email else ''
            allowed_domains = [tenant_owner_domain] if tenant_owner_domain else []

        if email_domain in allowed_domains:
            user.is_active = True 
            user.is_staff = True
        elif user.groups.filter(name__in=['partner', 'job_seeker', 'public', 'customer']).exists():
            user.is_active = True 
            user.is_staff = False
        else:
            messages.error(request, "Your email domain is not allowed for activation. Please contact your administrator.")
            return redirect('accounts:register')  

        user.save()
        messages.success(request, "Your account has been activated! You can work now.")
        login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
        return redirect('clients:tenant_expire_check')

    return render(request, 'accounts/registration/activation_invalid.html')








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
