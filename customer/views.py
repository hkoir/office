from django.shortcuts import render,redirect,get_object_or_404
from.forms import AddCustomerForm,AddLocationForm,UpdateLocationForm
from.models import Customer,Location
from django.core.paginator import Paginator
from django.contrib import messages

from .models import CustomerPerformance
from .forms import CustomerPerformanceForm 
from django.contrib.auth.decorators import login_required,permission_required




@login_required
def customer_dashboard(request):
    return render(request,'customer/customer_dashboard.html')



@login_required
def create_customer(request, id=None):  
    instance = get_object_or_404(Customer, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddCustomerForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance=form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()        
        messages.success(request, message_text)
        return redirect('customer:create_customer')  

    datas = Customer.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'customer/create_customer.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_customer(request, id):
    instance = get_object_or_404(Customer, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('customer:create_customer')  

    messages.warning(request, "Invalid delete request!")
    return redirect('customer:create_customer')  



@login_required
def create_location(request, id=None):  
    instance = get_object_or_404(Location, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddLocationForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance=form.save(commit=False)
        form_instance.save()   
        form_instance.user = request.user     
        messages.success(request, message_text)
        return redirect('customer:create_location')  

    datas = Location.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'customer/create_location.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_location(request, id):
    instance = get_object_or_404(Location, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('customer:create_location')   

    messages.warning(request, "Invalid delete request!")
    return redirect('customer:create_location')  



@login_required
def customer_performance_list(request):
    performances = CustomerPerformance.objects.all().order_by('-created_at')
    paginator = Paginator(performances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'customer/customer_performance_list.html', {'page_obj': page_obj})


@login_required
def add_or_update_performance(request, performance_id=None):
    if performance_id:
        performance = get_object_or_404(CustomerPerformance, id=performance_id)
        message_text = "Customer performance updated successfully!"
    else:
        performance = None
        message_text = "Customer performance added successfully!"
        
    form = CustomerPerformanceForm(request.POST or None, instance=performance)

    if request.method == 'POST':
        if form.is_valid():
            form_instance=form.save(commit=False)
            form_instance.user=request.user
            form_instance.save()
            messages.success(request, message_text)
            return redirect('customer:customer_performance_list')

    return render(request, 'customer/create_or_update_performance.html', {'form': form, 'performance': performance})


