from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from datetime import date, timedelta,datetime
from django.utils.timezone import now
from django.http import JsonResponse
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.contrib import messages
from decimal import Decimal


from django.db.models import Sum, Avg,Count,Q,Case, When, IntegerField,F,Max,DurationField, DecimalField,FloatField,ExpressionWrapper,Value,fields
from.forms import VehicleFaulttForm,PGRViewForm
from django.db import transaction

from django.conf import settings
from transport.utils import calculate_penalty_amount
import json
import csv
from collections import defaultdict
import calendar

from myproject.utils import create_notification

from .models import Transport, TransportRequest, ManagerApproval, BookingHistory,TransportUsage,Penalty
from.models import VehicleRentalCost,FuelPumpPayment,FuelPumpDatabase,FuelRefill,Vehiclefault

from.forms import FuelPumpPaymentForm,VehiclePaymentForm,FuelPumpSearchForm,FuelWithdrawForm,vehicleSummaryReportForm
from.forms import FuelRefillForm,FuelPumpDatabaseForm,TransportRequestStatusUpdateForm
from .forms import TransportExtensionForm,TransportUsageForm,TransportilterForm
from .forms import TransportRequestForm, ManagerApprovalForm,CreateTransportForm

from django.urls import reverse


@login_required
def transport_dashboard(request):
    menu_items = [
        {'title': 'Create Transport', 'url': reverse('transport:create_transport'), 'icon': 'fa-plus-circle', 'color': '#007bff'},
        {'title': 'Available Transport', 'url': reverse('transport:available_transports'), 'icon': 'fa-truck', 'color': '#28a745'},
        {'title': 'Transport Request', 'url': reverse('transport:create_transport_request'), 'icon': 'fa-file-signature', 'color': '#ffc107'},
        {'title': 'Booking History', 'url': reverse('transport:booking_history'), 'icon': 'fa-history', 'color': '#17a2b8'},
        {'title': 'Penalty History', 'url': reverse('transport:penalty_history'), 'icon': 'fa-gavel', 'color': '#dc3545'},
        {'title': 'Create Fuel Pump Database', 'url': reverse('transport:create_fuel_pump_database'), 'icon': 'fa-gas-pump', 'color': '#6f42c1'},
        {'title': 'Fuel Refill', 'url': reverse('transport:create_fuel_refill'), 'icon': 'fa-fill-drip', 'color': '#fd7e14'},
        {'title': 'Vehicle Fault Record', 'url': reverse('transport:create_vehicle_fault'), 'icon': 'fa-car-crash', 'color': '#20c997'},
        {'title': 'Vehicle Payment Update', 'url': reverse('transport:create_vehicle_payment'), 'icon': 'fa-credit-card', 'color': '#6610f2'},
        {'title': 'Fuel by Pump', 'url': reverse('transport:fuel_by_pump'), 'icon': 'fa-oil-can', 'color': '#e83e8c'},
        {'title': 'Datewise Fuel Consumed', 'url': reverse('transport:datewise_fuel_withdraw'), 'icon': 'fa-calendar-alt', 'color': '#007bff'},
        {'title': 'Overtime', 'url': reverse('transport:vehicle_overtime_calc'), 'icon': 'fa-stopwatch', 'color': '#28a745'},
        {'title': 'Vehicle Grand Summary', 'url': reverse('transport:vehicle_grand_summary'), 'icon': 'fa-chart-line', 'color': '#17a2b8'},
        {'title': 'Management Report', 'url': reverse('transport:management_summary_report'), 'icon': 'fa-file-invoice', 'color': '#ffc107'},
    ]
    return render(request, 'fleetmanagement/transport_dashboard.html', {'menu_items': menu_items})


@login_required
def manage_transport(request, id=None):    

    if request.method == 'POST' and 'delete_id' in request.POST:
        instance = get_object_or_404(Transport, id=request.POST.get('delete_id'))
        instance.delete()
        messages.success(request, "Deleted successfully")
        return redirect('transport:create_transport')

    instance = get_object_or_404(Transport, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"
    
    form = CreateTransportForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()
        messages.success(request, message_text)
        return redirect('transport:create_transport')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number= request.GET.get('vehicle_number')
    data = Transport.objects.all().order_by('vehicle_registration_date')

    if start_date and end_date:
        data = data.filter(created_at__range=(start_date,end_date))
      
    if vehicle_number:
        data = data.filter(vehicle_registration_number = vehicle_number)
        
    
       
    paginator = Paginator(data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'fleetmanagement/manage_transport.html', {
        'form': form,
        'instance': instance,
        'data': data,
        'page_obj': page_obj,      
    })




@login_required
def delete_transport(request, id):
    instance = get_object_or_404(Transport, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('transport:create_transport')
  
    messages.warning(request, "Invalid delete request!")
    return redirect('transport:create_transport')




@login_required
def available_transports(request):
    form = TransportilterForm(request.GET)
    start_date=None
    end_date = None
    vehicle_code = None
    vehicle_registration_number = None

    transports = Transport.objects.all().order_by('-vehicle_registration_date')

    total_vehicles = transports.count()    
    total_in_service_vehicles = transports.filter(status='IN-USE').count()
    total_available_vehicles = transports.filter(status='AVAILABLE').count()
    total_faulty_vehicles = transports.filter(status='FAULTY').count()

     

    if request.method == 'GET':
        form = TransportilterForm(request.GET)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            vehicle_code = form.cleaned_data['vehicle_code']
            status = form.cleaned_data['status']
            vehicle_registration_number = form.cleaned_data['vehicle_registration_number']
                   
            if start_date and end_date:
                transports = transports.filter(vehicle_registration_date__range=(start_date, end_date))  
            
            elif vehicle_code:
                transports = transports.filter(vehicle_code = vehicle_code)
            elif vehicle_registration_number:
                transports = transports.filter(vehicle_registration_number = vehicle_registration_number)
            elif status == 'AVAILABLE':
                transports = transports.filter(status = 'AVAILABLE')
            elif status == 'IN-USE':
                transports = transports.filter(status = 'IN-USE')
            elif status == 'ALL':
                transports = transports
        else:
            form = TransportilterForm()

           
             
    paginator = Paginator(transports, 8)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = TransportilterForm()
    return render(request, 'fleetmanagement/available_transports.html', 
        {
        'transports': transports,
        'form':form,
        'page_obj':page_obj,
        'total_vehicles':total_vehicles,
        'total_in_service_vehicles':total_in_service_vehicles,
        'total_available_vehicles':total_available_vehicles,
        'total_faulty_vehicles':total_faulty_vehicles
        })




def transport_details(request, transport_id):
    try:
        transport = Transport.objects.get(id=transport_id)     
        data = {
            "transport_id": transport.id,
            "vehicle_code": transport.vehicle_code,        
            "vehicle_registration_number": transport.vehicle_registration_number,
            "vehicle_registration_date": transport.vehicle_registration_date,
         
            "joining_date": transport.joining_date,
            "vehicle_description": transport.vehicle_description,
          
            'capacity':transport.capacity,
            'location':transport.location,
            'last_maintenance_date':transport.last_maintenance_date ,
            'vehicle_mileage':transport.vehicle_mileage,
            'status':transport.status,

            'driver_name':transport.driver_name,
            'driver_phone':transport.driver_phone ,
            'vehicle_ownership':transport.vehicle_ownership,
            'supervisor_name':transport.supervisor_name,
            'supervisor_phone':transport.supervisor_phone,

        }
 
        return JsonResponse(data)
    except Transport.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)
   

@login_required
def create_transport_request(request, id=None): 
    instance = get_object_or_404(TransportRequest, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"

    requests = TransportRequest.objects.none()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number = request.GET.get('vehicle_number')

    if request.user.groups.filter(name='Managers').exists():
        requests = TransportRequest.objects.all().order_by('-created_at')       
    else:
        requests = TransportRequest.objects.filter(staff=request.user).order_by('-created_at') 

    if start_date and end_date:
        requests = requests.filter(created_at__range=(start_date, end_date)).order_by('-created_at')
    if vehicle_number:
        requests = requests.filter(vehicle__vehicle_registration_number=vehicle_number).order_by('-created_at')
    
    form = TransportRequestForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        vehicle = form.cleaned_data['vehicle']
        desired_request_datetime = form.cleaned_data['request_datetime']
        desired_return_datetime = form.cleaned_data['return_datetime']
        
        overlapping_bookings = TransportRequest.objects.filter(
            vehicle=vehicle,
            status__in=['BOOKED', 'IN-USE'],
            request_datetime__lt=desired_return_datetime,
            return_datetime__gt=desired_request_datetime
        ).exclude(id=instance.id if instance else None).exists()

        if overlapping_bookings:
            messages.error(request, "The vehicle is already booked within the selected date range.")
        else:   
            transport_request = form.save(commit=False)
            transport_request.staff = request.user
            transport_request.save()
            messages.success(request, f"Transport request {message_text}")
            create_notification(
                request.user,
                message=f'Transport requested by {transport_request.staff},Car number: {transport_request.vehicle.vehicle_registration_number},\
                start time: {transport_request.request_datetime}, endtime:{transport_request.return_datetime}',                
                notification_type='TRANSPORT-NOTIFICATION'
                 )
            # send_email_to_manager()
            return redirect('transport:create_transport_request')
           
    paginator = Paginator(requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'fleetmanagement/create_transport_request.html', {
        'form': form,
        'instance': instance,
        'data': requests,
        'page_obj': page_obj,      
    })



@login_required
def delete_transport_request(request, id):
    instance = get_object_or_404(TransportRequest, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('transport:create_transport_request')
  
    messages.warning(request, "Invalid delete request!")
    return redirect('transport:create_transport_request')



@login_required
def create_transport_request_id(request, id=id): 
    instance = get_object_or_404(Transport, id=id) 
    message_text = "updated successfully!" if id else "added successfully!"

    requests = TransportRequest.objects.none()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number= request.GET.get('vehicle_number')

    if request.user.groups.filter(name='Managers').exists():
        requests = TransportRequest.objects.all().order_by('-created_at')       
    else:
        requests = TransportRequest.objects.filter(staff=request.user).order_by('-created_at')  
    if start_date and end_date:
            requests =requests.filter(created_at__range=(start_date,end_date)).order_by('-created_at')  
    if vehicle_number:
            requests = requests.filter(vehicle__vehicle_registration_number = vehicle_number).order_by('-created_at')  
    
    form = TransportRequestForm(request.POST)

    if request.method == 'POST' and form.is_valid():
        vehicle = form.cleaned_data['vehicle']
        desired_request_datetime = form.cleaned_data['request_datetime']
        desired_return_datetime = form.cleaned_data['return_datetime']
             
        overlapping_bookings = TransportRequest.objects.filter(
                vehicle=vehicle,
                status__in=['BOOKED', 'IN-USE'], 
                request_datetime__lt=desired_return_datetime,
                return_datetime__gt=desired_request_datetime
            ).exists()
        if overlapping_bookings:
                messages.warning(request, "The vehicle is already booked within the selected date range.")
        else:   
            transport_request = form.save(commit=False)
            transport_request.staff = request.user
            transport_request.save()
            messages.success(request, "Transport request created successfully!")
            create_notification(
                request.user,
                message=f'Transport requested by {transport_request.staff},Car number: {transport_request.vehicle.vehicle_registration_number},\
                start time: {transport_request.request_datetime}, endtime:{transport_request.return_datetime}',
                
                notification_type='TRANSPORT-NOTIFICATION'
                 )
            # send_email_to_manager()
            return redirect('transport:available_transports')        
    else:
        form = TransportRequestForm(initial={'vehicle': instance})           
       
    paginator = Paginator(requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    return render(request, 'fleetmanagement/create_transport_request_id.html', {
        'form': form,
        'instance': instance,
        'data':  requests,
        'page_obj': page_obj,      
    })



@login_required
def transport_request_approval(request, request_id):
    transport_request = get_object_or_404(TransportRequest, id=request_id)
    # if not request.user.groups.filter(name='Managers').exists():
    #     messages.info(request, "You do not have permission to approve this request.")
    #     return redirect('transport:transport_request_list')
    if request.method == 'POST':
        form = ManagerApprovalForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']

            try:
                approval = ManagerApproval.objects.get(request=transport_request)
                created = False
            except ManagerApproval.DoesNotExist:
                approval = ManagerApproval(
                    request=transport_request,
                    manager=request.user,
                    status=status,
                )
                created = True
            except ManagerApproval.MultipleObjectsReturned:
                approvals = ManagerApproval.objects.filter(request=transport_request)
                approval = approvals.first()
                approvals.exclude(id=approval.id).delete()
                created = False

            if not created:
                approval.manager = request.user
                approval.status = status

            approval.approve_request()
            approval.save()

            create_notification(
                request.user,
                message=f'Transport requested by {transport_request.staff}, has been confirmed, \
                Your driver is: {transport_request.vehicle.driver_name}, \
                Driver phone: {transport_request.vehicle.driver_phone}, \
                Car number: {transport_request.vehicle.vehicle_registration_number},\
                start time: {transport_request.request_datetime}, endtime:{transport_request.return_datetime}',
                
                notification_type='TRANSPORT-NOTIFICATION'
                 )
            # send_email_to_driver_user()
               
            transport_request.status = 'BOOKED'
            transport_request.save()
            transport_request.vehicle.status = 'BOOKED'
            transport_request.vehicle.save()
            messages.success(request, "Approval completed successfully!")

            return redirect('transport:create_transport_request')
    else:
        form = ManagerApprovalForm()
    return render(request, 'fleetmanagement/transport_request_approval.html', {'form': form, 'data': transport_request})

def send_email_to_driver_user():
    pass


from.models import TransportExtension
from.forms import TransportExtensionApprovaltForm

@login_required
def create_time_extension(request, id=None):
    booking = get_object_or_404(TransportRequest, id=id) if id else None
    time_extensions = booking.time_extension.all() if booking else TransportExtension.objects.none()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number = request.GET.get('vehicle_number')

    if start_date and end_date:
        time_extensions = time_extensions.filter(created_at__range=(start_date, end_date))
    if vehicle_number:
        time_extensions = time_extensions.filter(booking__vehicle__vehicle_registration_number=vehicle_number)

    if request.method == 'POST':
        form = TransportExtensionForm(request.POST)
        if form.is_valid():  
            extension = form.save(commit=False)
            extension.booking = booking
            extension.save()     

            if booking.return_datetime < now():
                booking.status = 'PENALIZED'
                booking.vehicle.status = 'PENALIZED'
            elif now() <= booking.return_datetime >= booking.request_datetime:
                booking.status = 'IN-USE'
                booking.vehicle.status = 'IN-USE'

            booking.save()
            booking.vehicle.save()
            return redirect('transport:create_transport_request')
    else:
        form = TransportExtensionForm()
    paginator = Paginator(time_extensions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'fleetmanagement/create_time_extension.html', {
        'form': form,
        'booking': booking,
        'page_obj': page_obj,
    })




@login_required
def approve_time_extension(request, id):
    instance = get_object_or_404(TransportExtension, id=id)
    form=TransportExtensionApprovaltForm(request.POST,instance=instance)
   
    if request.method == 'POST':       
        if form.is_valid():
            extended_until=form.cleaned_data['extended_until']
            form = form.save(commit=False)
            form.approved_by = request.user
            form.save()           
            instance.booking.return_datetime = extended_until
            instance.booking.save()

            if instance.booking.return_datetime < now():
                instance.booking.status = 'PENALIZED'
                instance.booking.vehicle.status = 'PENALIZED'
            elif now() <= instance.booking.return_datetime >= instance.booking.request_datetime:
                instance.booking.status = 'IN-USE'
                instance.booking.vehicle.status = 'IN-USE'

            instance.booking.save()
            instance.booking.vehicle.save()
           

            create_notification(
                request.user,
                message=f'Transport time extension approved by { request.user}',       
                notification_type='TRANSPORT-NOTIFICATION'
                 )        
            messages.success(request, "Approval action successfully saved!")
            return redirect('transport:create_transport_request')
        else:
            form=TransportExtensionApprovaltForm(instance=instance)
  
    form=TransportExtensionApprovaltForm(instance=instance)
    return render(request,'fleetmanagement/transport_extension_approval.html',{'form':form})



from.forms import PenaltyPaymentForm
def penalty_payment(request,penalty_id):
    penalty_instance = get_object_or_404(Penalty,id=penalty_id)
    form =PenaltyPaymentForm(request.POST,request.FILES,instance = penalty_instance)

    if request.method == 'POST':
        form = form =PenaltyPaymentForm(request.POST,request.FILES)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.staff = request.user
            form_instance.penalty.payment_status =True
            form_instance.save()
            return redirect('transport:penalty_history')
        else:
            print(form.error)          
    initial={
        'penalty':penalty_instance
    }
    form =PenaltyPaymentForm(initial=initial)
    return render(request,'fleetmanagement/penalty_payment.html',{'form':form})



def generate_calendar(year, month, booked_dates, in_use_dates):
    cal = calendar.Calendar()
    month_days = cal.itermonthdates(year, month)    
    calendar_data = []
    week = []
    for day in month_days:
        week.append({
            'date': day,
            'is_booked': day in booked_dates,
            'is_in_use': day in in_use_dates,
            'in_month': day.month == month  
        })
        if len(week) == 7: 
            calendar_data.append(week)
            week = []

    return calendar_data


def vehicle_booking_calendar(request, id):
    vehicle = get_object_or_404(Transport, id=id)
    current_date = date.today()
    year, month = current_date.year, current_date.month

    calendar_data_for_year = {}
    for m in range(1, 13): 
        booked_dates = []
        in_use_dates = []
        bookings = TransportRequest.objects.filter(
            vehicle=vehicle,
            status__in=['BOOKED', 'IN-USE'],
            request_datetime__year=year,
            request_datetime__month=m
        ).values('request_datetime', 'return_datetime', 'status')

        for booking in bookings:
            start_date = booking['request_datetime'].date()
            end_date = booking['return_datetime'].date()
            while start_date <= end_date:
                if booking['status'] == 'BOOKED':
                    booked_dates.append(start_date)
                elif booking['status'] == 'IN-USE':
                    in_use_dates.append(start_date)
                start_date += timedelta(days=1)

        calendar_data_for_year[m] = generate_calendar(year, m, booked_dates, in_use_dates)

    month_names = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
        }

    return render(request, 'fleetmanagement/vehicle_calendar.html', {
        'vehicle': vehicle,
        'calendar_data_for_year': calendar_data_for_year,
        'year': year,
        'month': month,
        'month_names': month_names,
    })



@login_required
def update_booking(request, booking_id):
    booking = get_object_or_404(TransportRequest, id=booking_id)
    if request.method == 'POST':
        form = TransportRequestStatusUpdateForm(request.POST, instance=booking)        
        if form.is_valid():
            status = form.cleaned_data['status']
            
            if status == 'COMPLETED':
                booking.staff = request.user 
                booking.actual_return = timezone.now()  
                booking.status = 'COMPLETED'  
                booking.vehicle.status = 'AVAILABLE'  
                
                booking.save()
                booking.vehicle.save()
                try:
                    penalty_amount = calculate_penalty_amount(booking)
                except Exception as e:
                    messages.error(request, f"Error calculating penalty: {str(e)}")
                    penalty_amount = 0
               
                if penalty_amount > 0:

                    booking_penalty, created =Penalty.objects.get_or_create(
                        transport_request=booking,
                        defaults={
                            'issued_at': now(),
                            'penalty_amount': penalty_amount,
                            'staff':booking.staff,
                            'reason':'Overdue return...'
                        }
                    )
                    if not created:
                        booking_penalty.penalty_amount =penalty_amount                
                        booking_penalty.reason = 'Overdue return...'
                        booking_penalty.issued_at = timezone.now()
                        booking_penalty.staff=booking.staff
                        booking_penalty.save()
            
            return redirect('transport:available_transports')
    else:
        form = TransportRequestStatusUpdateForm(instance=booking)
    return render(request, 'fleetmanagement/update_transport_booking.html', {'form': form, 'transport': booking})




def refresh_status(request):
    bookings_to_start = TransportRequest.objects.select_related('vehicle').all()    
    with transaction.atomic():  
        for booking in bookings_to_start:
            if booking.return_datetime > now() and booking.request_datetime <= now():
                booking.vehicle.status = 'IN-USE'
                booking.status = 'IN-USE'
                if booking.status == 'COMPLETED':
                     booking.vehicle.status = 'AVAILABLE'
            

            elif booking.status == 'COMPLETED':
                booking.vehicle.status = 'AVAILABLE'

            elif booking.return_datetime < now() and booking.status != 'COMPLETED':
                booking.vehicle.status = 'PENALIZED'
                booking.status = 'PENALIZED'
                penalty_amount = calculate_penalty_amount(booking)
                booking_penalty, created =Penalty.objects.get_or_create(
                    transport_request=booking,
                    defaults={
                        'issued_at': now(),
                        'penalty_amount': penalty_amount,
                        'staff':booking.staff.username,
                        'reason':'Overdue return...'
                    }
                )
                if not created:
                    booking_penalty.penalty_amount =penalty_amount                
                    booking_penalty.reason = 'Overdue return...'
                    booking_penalty.issued_at = timezone.now()
                    booking_penalty.staff=booking.staff
                    booking_penalty.save()

            booking.vehicle.save()
            booking.save()
    return redirect('transport:available_transports')



@login_required
def transport_usage_update(request, booking_id):
    booking = get_object_or_404(TransportRequest, id=booking_id)

    if request.method == 'POST':
        form = TransportUsageForm(request.POST)
        
        if form.is_valid():
            status = form.cleaned_data['status']
            end_reading= form.cleaned_data['end_reading']
            form = form.save(commit=False)
            form.booking = booking 
          
            if status == 'COMPLETED':
                booking.status = 'COMPLETED'
                booking.vehicle.status = 'AVAILABLE'
                booking.save()
                booking.vehicle.save()

            if status == 'IN-USE':
                booking.vehicle.status = 'IN-USE'
                booking.status = 'IN-USE'
                booking.save()
                booking.vehicle.save()

            if end_reading:
                booking.vehicle.vehicle_mileage = end_reading
                booking.vehicle.save()

            form.save()

            booking_history, created = BookingHistory.objects.get_or_create(
                booking=booking,
                defaults={'transport_used': booking.vehicle, 'staff': request.user}
            )
          
            messages.success(request, "Transport usage details created successfully.")
            return redirect('transport:create_transport_request')
    else:  
        initial_data = {
            'travel_date': timezone.now().date(), 
            'booking':booking          
        }
        form = TransportUsageForm(initial=initial_data)
    return render(request, 'fleetmanagement/transport_usage_update.html', {'form': form, 'booking': booking})




@login_required
def booking_history(request):
    form = TransportilterForm(request.POST)
    history = BookingHistory.objects.filter(staff=request.user)
    if request.method == 'POST':
        form = TransportUsageForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_dat']
            end_date = form.cleaned_data['end_dat']
    return render(request, 'fleetmanagement/booking_history.html', {'history': history,'form':form})


@login_required
def penalty_history(request):
    form = TransportilterForm(request.POST)
    history = Penalty.objects.filter(staff=request.user).order_by('-created_at')
    if request.method == 'POST':
        form = TransportUsageForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_dat']
            end_date = form.cleaned_data['end_dat']
    form = TransportilterForm()
    return render(request, 'fleetmanagement/penalty_history.html', {'history': history,'form':form})




@login_required
def manage_fuel_pump(request, id=None):   
    if request.method == 'POST' and 'delete_id' in request.POST:
        instance = get_object_or_404(FuelPumpDatabase, id=request.POST.get('delete_id'))
        instance.delete()
        messages.success(request, "Deleted successfully")
        return redirect('transport:create_fuel_pump_database')

    instance = get_object_or_404(FuelPumpDatabase, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"
    
    form = FuelPumpDatabaseForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()
        messages.success(request, message_text)
        return redirect('transport:create_fuel_pump_database')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    fuel_pump_name= request.GET.get('fuel_pump_name')
    data = FuelPumpDatabase.objects.all().order_by('fuel_pump_name')

    if start_date and end_date:
        data = data.filter(created_at__range=(start_date,end_date))
    if fuel_pump_name:
        data = data.filter(fuel_pump_name =  fuel_pump_name)
    
       
    paginator = Paginator(data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'fleetmanagement/manage_fuel_pump.html', {
        'form': form,
        'instance': instance,
        'data': data,
        'page_obj': page_obj
    })

@login_required
def delete_fuel_pump(request, id):
    instance = get_object_or_404(FuelPumpDatabase, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('transport:create_fuel_pump_database')

    messages.warning(request, "Invalid delete request!")
    return redirect('transport:create_fuel_pump_database')



def update_fuel_pump_database(request, pump_id):
    pump_instance = get_object_or_404(FuelPumpDatabase, id=pump_id)
    if request.method == 'POST':
        form = FuelPumpDatabaseForm(request.POST, request.FILES, instance=pump_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Entries updated successfully")
            return redirect('transport:view_fuel_pump')
    else:
        form = FuelPumpDatabaseForm(instance=pump_instance)
    return render(request, 'fleetmanagement/create_fuel_pump.html', {'form': form, 'pump_instance': pump_instance})


@login_required
def manage_fuel_refill(request,id=None): 
    vehicle_number=None   
    instance = get_object_or_404(FuelRefill, id=id) if id else None    

    if request.method == 'POST':        
        form = FuelRefillForm(request.POST or None, request.FILES or None, instance=instance)
        if form.is_valid():        
            form.instance.refill_requester = request.user           
            form.save()
            messages.success(request,'refill success')
            return redirect('transport:create_fuel_refill')

    fuel_refill = FuelRefill.objects.all().order_by('-created_at')
    
    vehicle_number = request.GET.get('vehicle_registration_number')   
    if vehicle_number:
         fuel_refill = fuel_refill.filter(vehicle__vehicle_registration_number=vehicle_number) 
    if 'download_csv' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="expense_approval_status.csv"'
        writer = csv.writer(response)
        writer.writerow(['created_at','Requester'])
        for expense_requisition in fuel_refill:
            writer.writerow([
                expense_requisition.created_at,
                expense_requisition.refill_requester,               
            ])
        return response
    paginator = Paginator( fuel_refill, 10) 
    page_number = request.GET.get('page')   
    fuel_refill = paginator.get_page(page_number)   
   
    form = FuelRefillForm(instance=instance)
    return render(request, 'fleetmanagement/manage_fuel_refill.html', {'fuel_refill':fuel_refill,'form':form})



def fuel_by_pump(request):
    form = FuelWithdrawForm()
    pg_fuel_data = []
    vehicle_fuel_data = []
    combined_fuel_data = []
    if request.method == 'POST':
        form = FuelWithdrawForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
           
            vehicle_fuel_data = FuelRefill.objects.filter(refill_date__range=[start_date, end_date]) \
                                .values('pump__id', 'pump__fuel_pump_name', 'pump__advance_amount_given') \
                                .annotate(total_fuel=Sum('refill_amount'), total_fuel_cost=Sum('fuel_cost')) \
                                .order_by('pump__fuel_pump_name')
            payments_data = FuelPumpPayment.objects.filter(payment_date__range=[start_date, end_date]) \
                                .values('pump__id', 'pump__fuel_pump_name') \
                                .annotate(total_payment=Sum('payment_amount')) \
                                .order_by('pump__fuel_pump_name')
    else:
       
        vehicle_fuel_data = FuelRefill.objects.values('pump__id', 'pump__fuel_pump_name', 'pump__advance_amount_given') \
                            .annotate(total_fuel=Sum('refill_amount'), total_fuel_cost=Sum('fuel_cost')) \
                            .order_by('pump__fuel_pump_name')
        payments_data = FuelPumpPayment.objects.values('pump__id', 'pump__fuel_pump_name') \
                            .annotate(total_payment=Sum('payment_amount')) \
                            .order_by('pump__fuel_pump_name')

    combined_data = defaultdict(lambda: {
        'total_fuel': 0.0,
        'total_fuel_cost': 0.0,
        'advance_amount_given': 0.0,
        'remaining_cost': 0.0,
        'total_payment': 0.0,
        'pump_id': None
    })

    for data in pg_fuel_data:
        fuel_pump_name = data['fuel_pump__fuel_pump_name'] or 'Local purchase'
        combined_data[fuel_pump_name]['total_fuel'] += float(data['total_fuel'] or 0)
        combined_data[fuel_pump_name]['total_fuel_cost'] += float(data['total_fuel_cost'] or 0)
        advance_amount_given = float(data.get('fuel_pump__advance_amount_given') or 0)
        combined_data[fuel_pump_name]['advance_amount_given'] = advance_amount_given
        combined_data[fuel_pump_name]['remaining_cost'] = advance_amount_given - combined_data[fuel_pump_name]['total_fuel_cost']
        combined_data[fuel_pump_name]['pump_id'] = data['fuel_pump__id']
    for data in vehicle_fuel_data:
        fuel_pump_name = data['pump__fuel_pump_name'] or 'Local purchase'
        combined_data[fuel_pump_name]['total_fuel'] += float(data['total_fuel'] or 0)
        combined_data[fuel_pump_name]['total_fuel_cost'] += float(data['total_fuel_cost'] or 0)
        advance_amount_given = float(data.get('pump__advance_amount_given') or 0)
        combined_data[fuel_pump_name]['advance_amount_given'] = advance_amount_given
        combined_data[fuel_pump_name]['remaining_cost'] = advance_amount_given - combined_data[fuel_pump_name]['total_fuel_cost']
        combined_data[fuel_pump_name]['pump_id'] = data['pump__id']
    for data in payments_data:
        fuel_pump_name = data['pump__fuel_pump_name'] or 'Local purchase'
        combined_data[fuel_pump_name]['total_payment'] += float(data['total_payment'] or 0)
        combined_data[fuel_pump_name]['remaining_cost'] += float(data['total_payment'] or 0)

    combined_fuel_data = [
        {
            'fuel_pump_name': pump_name,
            'total_fuel': data['total_fuel'],
            'total_fuel_cost': data['total_fuel_cost'],
            'advance_amount_given': data['advance_amount_given'],
            'remaining_cost': data['remaining_cost'],
            'total_payment': data['total_payment'],
            'pump_id': data['pump_id']
        }
        for pump_name, data in combined_data.items()
    ]
    combined_fuel_data.sort(key=lambda x: x['fuel_pump_name'])
    return render(request, 'fleetmanagement/fuel_withdraw_by_pump.html', {
        'form': form,
        'combined_fuel_data': combined_fuel_data,
        'pg_fuel_data': pg_fuel_data,
        'vehicle_fuel_data': vehicle_fuel_data
    })



def datewise_fuel_withdraw(request):
    pg_fuel_data = []
    vehicle_fuel_data = []
    if request.method == 'POST':
        form = FuelPumpSearchForm(request.POST)
        if form.is_valid():
            fuel_pump_name = form.cleaned_data['fuel_pump_name']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
          
            vehicle_fuel_data = FuelRefill.objects.filter(
                pump__fuel_pump_name=fuel_pump_name,
                refill_date__range=[start_date, end_date]
            ).order_by('refill_date')

            return render(request, 'fleetmanagement/datewise_fuel_withdraw.html', {
                'form': form,
                'pg_fuel_data': pg_fuel_data,
                'vehicle_fuel_data': vehicle_fuel_data,
                'fuel_pump_name': fuel_pump_name,
            })
    else:
        form = FuelPumpSearchForm()
    return render(request, 'fleetmanagement/datewise_fuel_withdraw.html', {'form': form})



@login_required
def create_fuel_pump_payment(request, id=None):
    pump_payment_data = FuelPumpPayment.objects.all().order_by('-created_at')  
    instance = get_object_or_404(FuelPumpPayment, id=id) if id else None
    message_text = "Updated successfully!" if id else "Added successfully!"
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    pump_number= request.GET.get('vehicle_number')

    if start_date and end_date:
        pump_payment_data = pump_payment_data.filter(created_at__range=(start_date,end_date))
    if pump_number:
        pump_payment_data = pump_payment_data.filter(pump__fuel_pump_name = pump_number)
   
    form = FuelPumpPaymentForm(request.POST or None, request.FILES or None, instance=instance)
   
    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()  
        messages.success(request, message_text)        
        return redirect('transport:create_fuel_pump_payment')  
    
    paginator = Paginator(pump_payment_data, 10) 
    page_number = request.GET.get('page')   
    page_obj = paginator.get_page(page_number) 
    form = FuelPumpPaymentForm(instance=instance)
    return render(request, 'fleetmanagement/manage_fuel_pump_payment.html', {
        'form': form,
        'instance': instance,   
        'page_obj':page_obj
    })



@login_required
def delete_fuel_pump_payment(request, id):
    instance = get_object_or_404(FuelPumpPayment, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('transport:create_transport')
  
    messages.warning(request, "Invalid delete request!")
    return redirect('transport:create_fuel_pump_payment')  





@login_required
def create_vehicle_payment(request, id=None):
    vehicle_payment_data = VehicleRentalCost.objects.all().order_by('-created_at')  
    instance = get_object_or_404(VehicleRentalCost, id=id) if id else None
    message_text = "Updated successfully!" if id else "Added successfully!"
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number= request.GET.get('vehicle_number')
    if start_date and end_date:
        vehicle_payment_data = vehicle_payment_data.filter(created_at__range=(start_date,end_date))
    if vehicle_number:
        vehicle_payment_data = vehicle_payment_data.filter(vehicle__vehicle_registration_number = vehicle_number)
   
    form = VehiclePaymentForm(request.POST or None, request.FILES or None, instance=instance)
   
    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()  
        messages.success(request, message_text)        
        return redirect('transport:create_vehicle_payment')  
    
    paginator = Paginator( vehicle_payment_data, 10) 
    page_number = request.GET.get('page')   
    page_obj = paginator.get_page(page_number) 
    form = VehiclePaymentForm(instance=instance)
    return render(request, 'fleetmanagement/manage_vehicle_payment.html', {
        'form': form,
        'instance': instance,
        'vehicle_payment_data': vehicle_payment_data,
        'page_obj':page_obj
    })



@login_required
def delete_vehicle_payment(request, id):
    instance = get_object_or_404(VehicleRentalCost, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('transport:create_transport')
  
    messages.warning(request, "Invalid delete request!")
    return redirect('transport:create_vehicle_payment')  





@login_required
def create_vehicle_fault(request, id=None):
    vehiclefault = Vehiclefault.objects.all()  .order_by('-created_at')  
    instance = get_object_or_404(Vehiclefault, id=id) if id else None
    message_text = "Updated successfully!" if id else "Added successfully!"

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    vehicle_number= request.GET.get('vehicle_number')

    if start_date and end_date:
        vehiclefault = vehiclefault.filter(created_at__range=(start_date,end_date))
    if vehicle_number:
        vehiclefault = vehiclefault.filter(vehicle__vehicle_registration_number = vehicle_number)
   
    form = VehicleFaulttForm(request.POST or None, request.FILES or None, instance=instance)
   
    if request.method == 'POST' and form.is_valid():
        form_instance = form.save(commit=False)
        form_instance.user = request.user
        form_instance.save()  
        messages.success(request, message_text)        
        return redirect('transport:create_vehicle_fault')  
    
    paginator = Paginator(vehiclefault, 10) 
    page_number = request.GET.get('page')   
    page_obj = paginator.get_page(page_number) 
    form = VehicleFaulttForm(instance=instance)
    return render(request, 'fleetmanagement/create_vehicle_fault.html', 
    {
        'form': form,
        'page_obj':page_obj,
        'instance':instance
       
    })




def vehicle_overtime_calc(request):
    days = None
    start_date = None
    end_date = None   
    vehicle_rent_per_day = None
   
    form = vehicleSummaryReportForm(request.GET or {'days': 60})  
   
    running_data_queryset = TransportUsage.objects.all().order_by('-created_at')
   
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')
     
        vehicle_number = form.cleaned_data.get('vehicle_number')
        if start_date and end_date:
            running_data_queryset =  running_data_queryset.filter(created_at__range=(start_date, end_date))
            days = (end_date - start_date).days + 1
        elif days:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=days)
            running_data_queryset = running_data_queryset.filter(created_at__range=(start_date, end_date))
        
        if vehicle_number:
             running_data_queryset =  running_data_queryset.filter(vehicle__vehicle_reg_number=vehicle_number)
    
    datewise_running_data = {}
    vehicle_totals = {}
    friday_saturday = None
    overtime_cost =0.0


    for data in running_data_queryset:    
        date = data.travel_date
        friday_saturday = date.weekday() in [4, 5]
        vehicle_reg_number = data.booking.vehicle.vehicle_registration_number  
        running_hours = Decimal(data.running_hours or 0)
        overtime_rate = Decimal(data.booking.vehicle.vehicle_driver_overtime_rate)
        body_overtime_rate = Decimal(data.booking.vehicle.vehicle_body_overtime_rate)
       
        kilometer_run = Decimal(data.kilometer_run) or 0
        total_CNG_cost =data.kilometer_cost_CNG or 0
        total_gasoline_cost =data.kilometer_cost_gasoline or 0
        total_kilometer_cost = data.kilometer_cost or 0
        travel_purpose = data.booking.purpose    
        vehicle_rent_per_day = Decimal(data.booking.vehicle.vehicle_rent) / Decimal(30)
       
             
        
        if vehicle_reg_number not in datewise_running_data:
            datewise_running_data[vehicle_reg_number] = {}
        if date not in datewise_running_data[vehicle_reg_number]:
            datewise_running_data[vehicle_reg_number][date] = {
                'total_running_hours': Decimal(0), 
                'overtime_running_hours': Decimal(0),
                'overtime_cost': Decimal(0), 
                'body_overtime_cost': Decimal(0), 
                'vehicle_rent_per_day': Decimal(0),                            
                'kilometer_run': kilometer_run,
                'travel_purpose': travel_purpose,
                'remarks': '',
                'overtime_rate': Decimal(0),
                'body_overtime_rate': Decimal(0),
                'total_cost': Decimal(0), 
                'total_CNG_cost':0,
                'total_gasoline_cost':0,
                'total_kilometer_cost':0,
                'grand_total_cost':0
            }

        datewise_running_data[vehicle_reg_number][date]['total_running_hours'] += running_hours
        if friday_saturday: 
            overtime_running_hours = running_hours
            remarks = 'Weekend'           
        else:
            overtime_running_hours = max(Decimal(0), datewise_running_data[vehicle_reg_number][date]['total_running_hours'] - Decimal(8)) 
            remarks = 'Weekday'        
        overtime_cost = overtime_rate * overtime_running_hours
        body_overtime_cost = body_overtime_rate * overtime_running_hours
        
        datewise_running_data[vehicle_reg_number][date]['overtime_running_hours'] += overtime_running_hours
        datewise_running_data[vehicle_reg_number][date]['overtime_cost'] += overtime_cost
        datewise_running_data[vehicle_reg_number][date]['body_overtime_cost'] += body_overtime_cost
        datewise_running_data[vehicle_reg_number][date]['overtime_rate'] = overtime_rate
        datewise_running_data[vehicle_reg_number][date]['body_overtime_rate'] = body_overtime_rate
        datewise_running_data[vehicle_reg_number][date]['vehicle_rent_per_day'] = vehicle_rent_per_day

        datewise_running_data[vehicle_reg_number][date]['total_CNG_cost'] += total_CNG_cost
        datewise_running_data[vehicle_reg_number][date]['total_gasoline_cost'] += total_gasoline_cost
        datewise_running_data[vehicle_reg_number][date]['total_kilometer_cost'] += total_kilometer_cost
       
        datewise_running_data[vehicle_reg_number][date]['remarks'] = remarks

        datewise_running_data[vehicle_reg_number][date]['total_cost'] = (
            datewise_running_data[vehicle_reg_number][date]['overtime_cost'] + 
            datewise_running_data[vehicle_reg_number][date]['body_overtime_cost'] + 
            vehicle_rent_per_day
        )

        datewise_running_data[vehicle_reg_number][date]['grand_total_cost'] = (
            datewise_running_data[vehicle_reg_number][date]['overtime_cost'] + 
            datewise_running_data[vehicle_reg_number][date]['body_overtime_cost'] + 
            vehicle_rent_per_day +
            datewise_running_data[vehicle_reg_number][date]['total_kilometer_cost']
        )


    #   below is for grand summary
    total_overtime_cost =0
    total_body_overtime_cost=0
    total_rent_cost=0
    total_vehicle_cost=0
    total_kilometer_cost=0
    for vehicle_reg_number, dates in datewise_running_data.items():
        total_overtime_cost = sum(date_data['overtime_cost'] for date_data in dates.values())
        total_body_overtime_cost = sum(date_data['body_overtime_cost'] for date_data in dates.values())
        total_rent_cost = sum(date_data['vehicle_rent_per_day'] for date_data in dates.values())

        total_kilometer_cost = sum(date_data['total_kilometer_cost'] for date_data in dates.values())
        grand_total_cost = sum(date_data['grand_total_cost'] for date_data in dates.values())

        total_vehicle_cost = total_overtime_cost +  total_body_overtime_cost + total_rent_cost
        grand_total_summary=grand_total_cost
        
        vehicle_totals[vehicle_reg_number] = {
            'total_overtime_cost': total_overtime_cost,
            'total_body_overtime_cost': total_body_overtime_cost,
            'total_rent_cost': total_rent_cost,
            'total_vehicle_cost': total_vehicle_cost,
            'total_kilometer_cost': total_kilometer_cost,
            'grand_total_summary': grand_total_summary,                                                        
        }
    
    datewise_running_data_list = [(vehicle_reg_number, data) for vehicle_reg_number, data in datewise_running_data.items()]
    vehicle_totals_list = [(vehicle_reg_number, total_overtime_amount) for vehicle_reg_number, total_overtime_amount in vehicle_totals.items()]
    
    chart_data = {
        'labels': [
          
            'total_overtime_cost',
            'total_body_overtime_cost',

            'total_rent_cost',
            'total_vehicle_cost',
            'total_kilometer_cost',
        ],
        'values': [
           
            float(total_overtime_cost),
            float(total_body_overtime_cost),
            float(total_rent_cost),
            float(total_vehicle_cost),
            float(total_kilometer_cost),
        ],
    }


    paginator = Paginator(datewise_running_data_list, 10)
    page = request.GET.get('page')   
    datewise_running_data = paginator.get_page(page)

    form = vehicleSummaryReportForm()
    context = {'datewise_running_data': datewise_running_data,
               'vehicle_totals_list': vehicle_totals_list,
               'form':form,
                'days': days,
                'start_date': start_date,
                'end_date': end_date,
                'chart_data': json.dumps(chart_data),
               }   
    return render(request, 'fleetmanagement/vehicle_overtime_calc.html', context)



@login_required
def vehicle_grand_summary(request):
    days = None
    start_date = None
    end_date = None
    region = None
    zone = None
    mp = None
    number_of_days = None
    vehicle_reg_number = None  
    month_number = None
    month_name = None
    year = None
    aggregated_data = {}
    form = vehicleSummaryReportForm(request.GET or {'days':60})
    vehicle_running_data = TransportUsage.objects.all()
    vehicle_fault_data = Vehiclefault.objects.all()      
    vehicle_refill_data = FuelRefill.objects.all() 
    vehicle_payment_data = VehicleRentalCost.objects.all()
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')       
        vehicle_number = form.cleaned_data.get('vehicle_number')    
        month_name = form.cleaned_data.get("month") 
        year = form.cleaned_data.get("year") 

        if month_name:          
            month_number = datetime.strptime(month_name, "%B").month  # Converts "January" to 1 

        if start_date and end_date:
            vehicle_running_data = vehicle_running_data.filter(created_at__range=(start_date, end_date))
            vehicle_fault_data = vehicle_fault_data.filter(created_at__range=(start_date, end_date))
            vehicle_refill_data = vehicle_refill_data.filter(created_at__range=(start_date, end_date))
            vehicle_payment_data = vehicle_payment_data.filter(created_at__range=(start_date, end_date))
        elif days:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=days)
            vehicle_running_data = vehicle_running_data.filter(created_at__range=(start_date, end_date))
            vehicle_fault_data = vehicle_fault_data.filter(created_at__range=(start_date, end_date))
            vehicle_refill_data = vehicle_refill_data.filter(created_at__range=(start_date, end_date))
        elif vehicle_number:
            vehicle_running_data = vehicle_running_data.filter(booking__vehicle__vehicle_registration_number=vehicle_number)
            vehicle_fault_data = vehicle_fault_data.filter(vehicle__vehicle_registration_number=vehicle_number)
            vehicle_refill_data = vehicle_refill_data.filter(vehicle__vehicle_registration_number=vehicle_number)
        
        elif month_number:
            vehicle_running_data = vehicle_running_data.filter(created_at__month=month_number)
            vehicle_fault_data = vehicle_fault_data.filter(created_at__month=month_number)
            vehicle_refill_data = vehicle_refill_data.filter(created_at__month=month_number)
            vehicle_payment_data = vehicle_payment_data.filter(created_at__month=month_number)
        
        elif year:
            vehicle_running_data = vehicle_running_data.filter(created_at__year=year)
            vehicle_fault_data = vehicle_fault_data.filter(created_at__year=year)
            vehicle_refill_data = vehicle_refill_data.filter(created_at__year=year)
            vehicle_payment_data = vehicle_payment_data.filter(created_at__year=year)

        total_CNG_cost=0
        total_gasoline_cost=0
        total_kilometer_cost=0
        processed_vehicles = {}

        for running_data in vehicle_running_data:
            if running_data.booking:               
                vehicle_reg_number = running_data.booking.vehicle.vehicle_registration_number
                driver_overtime_rate = running_data.booking.vehicle.vehicle_driver_overtime_rate
                vehicle_body_overtime_rate = running_data.booking.vehicle.vehicle_body_overtime_rate

                travel_date = running_data.travel_date
                if vehicle_reg_number not in processed_vehicles:
                    processed_vehicles[vehicle_reg_number] = set()  # Initialize empty set for this vehicle
                vehicle_rent = 0
                if travel_date not in processed_vehicles[vehicle_reg_number]:  
                    vehicle_rent = running_data.booking.vehicle.vehicle_rent / 30 or 0
                    processed_vehicles[vehicle_reg_number].add(travel_date)
               
                total_kilometer_run = running_data.kilometer_run or 0             
                # vehicle_rent = running_data.booking.vehicle.vehicle_rent / 30 or 0
               
                vehicle_rental_rate = running_data.booking.vehicle.vehicle_rent or 0
                total_CNG_cost = running_data.kilometer_cost_CNG or 0
                total_gasoline_cost = running_data.kilometer_cost_gasoline or 0
                total_kilometer_cost = running_data.kilometer_cost or 0
                total_fuel_consumed = running_data.fuel_consumed or 0
               
                friday_saturday = running_data.travel_date.weekday() in [4, 5]
                running_hours = running_data.running_hours or 0
                overtime_run_hours = running_hours if friday_saturday else max(0, running_hours - 8)
                overtime_cost = float(overtime_run_hours) * float(driver_overtime_rate)
                vehicle_body_overtime_cost = float(overtime_run_hours) * float(vehicle_body_overtime_rate)
                total_vehicle_bill_amount = float(vehicle_rent) + float(overtime_cost) + float(vehicle_body_overtime_cost)
                grand_total_bill_amount =  float(total_vehicle_bill_amount) + float(total_kilometer_cost)
                
                if vehicle_reg_number not in aggregated_data:
                    aggregated_data[vehicle_reg_number] = {
                        'vehicle_id': running_data.booking.vehicle.id,
                        'total_running_hours': 0,
                        'total_overtime_run_hours': 0,
                        'total_overtime_cost': 0,
                        'total_vehicle_rent_due': 0,
                        'total_vehicle_bill_amount': 0,
                        'driver_overtime_rate': [],
                        'vehicle_body_overtime_rate': [],                      
                        'vehicle_rental_rate': [],
                        'vehicle_rent': [],                       
                        'travel_dates': set(),
                        'num_travel_dates': 0,
                        'total_tickets_handle': 0,
                        'total_pg_runhour_handle': 0,
                        'total_fault_hours': 0,
                        'vehicle_rent_paid': 0,
                        'vehicle_body_overtime_paid': 0,
                        'vehicle_driver_overtime_paid': 0,
                        'total_bill_paid': 0,
                        'total_fuel_balance': 0,
                        'total_fuel_consumed': 0,
                        'total_kilometer_run': 0,
                        'total_kilometer_run_from_refill': 0,
                        'vehicle_body_overtime_cost': 0,
                        'total_fuel_refil': 0,
                        'total_fuel_consumed_from_refil': 0,
                        'total_fuel_balance_from_refil': 0,
                        'total_fuel_reserve_from_refil': 0,

                        'total_CNG_cost': 0,
                        'total_gasoline_cost': 0,
                        'total_kilometer_cost': 0,
                        'grand_total_bill_amount':0,

                        'total_fuel_reserve_from_refil': 0,
                       
                    }
                
                aggregated_data[vehicle_reg_number]['total_running_hours'] += running_hours
                aggregated_data[vehicle_reg_number]['total_kilometer_run'] += total_kilometer_run
                aggregated_data[vehicle_reg_number]['total_fuel_consumed'] += total_fuel_consumed
                aggregated_data[vehicle_reg_number]['total_overtime_run_hours'] += overtime_run_hours
                aggregated_data[vehicle_reg_number]['total_overtime_cost'] += overtime_cost
                aggregated_data[vehicle_reg_number]['vehicle_body_overtime_cost'] += vehicle_body_overtime_cost
               
                aggregated_data[vehicle_reg_number]['total_vehicle_rent_due'] += vehicle_rent
                
                aggregated_data[vehicle_reg_number]['total_vehicle_bill_amount'] += float(total_vehicle_bill_amount)
                aggregated_data[vehicle_reg_number]['total_CNG_cost'] += total_CNG_cost
                aggregated_data[vehicle_reg_number]['total_gasoline_cost'] += total_gasoline_cost
                aggregated_data[vehicle_reg_number]['total_kilometer_cost'] += total_kilometer_cost
                aggregated_data[vehicle_reg_number]['grand_total_bill_amount'] += grand_total_bill_amount
                aggregated_data[vehicle_reg_number]['driver_overtime_rate'].append(driver_overtime_rate)
                aggregated_data[vehicle_reg_number]['vehicle_body_overtime_rate'].append(vehicle_body_overtime_rate)
               
                aggregated_data[vehicle_reg_number]['vehicle_rent'].append(vehicle_rent)

                aggregated_data[vehicle_reg_number]['vehicle_rental_rate'].append(vehicle_rental_rate)
                aggregated_data[vehicle_reg_number]['travel_dates'].add(running_data.travel_date)
                aggregated_data[vehicle_reg_number]['num_travel_dates'] = len(aggregated_data[vehicle_reg_number]['travel_dates'])
               
               
               
        for payment_data in vehicle_payment_data:       
            if payment_data.vehicle:
                vehicle_reg_number = payment_data.vehicle.vehicle_registration_number            
                total_bill_paid = payment_data.vehicle_total_paid
                if vehicle_reg_number in aggregated_data:
                    aggregated_data[vehicle_reg_number]['total_bill_paid'] += total_bill_paid   
        for fault_data in vehicle_fault_data:        
            if fault_data.vehicle:
                vehicle_reg_number = fault_data.vehicle.vehicle_registration_number
                if vehicle_reg_number in aggregated_data:
                    aggregated_data[vehicle_reg_number]['total_fault_hours'] += fault_data.fault_duration_hours
       
        for fuel_refill in vehicle_refill_data:
            if fuel_refill.vehicle:
                vehicle_reg_number = fuel_refill.vehicle.vehicle_registration_number
                if vehicle_reg_number in aggregated_data:                   
                    total_fuel_consumed_from_refil = fuel_refill.vehicle_fuel_consumed
                    total_fuel_refil = fuel_refill.refill_amount
                    total_kilometer_run_from_refill = fuel_refill.vehicle_kilometer_run or 0
                    total_fuel_balance_from_refil = total_fuel_refil - total_fuel_consumed_from_refil
                   
                    aggregated_data[vehicle_reg_number]['total_fuel_refil'] += total_fuel_refil
                    aggregated_data[vehicle_reg_number]['total_kilometer_run_from_refill'] += total_kilometer_run_from_refill
                    aggregated_data[vehicle_reg_number]['total_fuel_consumed_from_refil'] += total_fuel_consumed_from_refil
                    aggregated_data[vehicle_reg_number]['total_fuel_balance_from_refil'] += total_fuel_balance_from_refil
        
        for vehicle_reg_number, data in aggregated_data.items():
            data['total_fuel_balance'] = data['total_fuel_refil'] - data['total_fuel_consumed']      
    
    aggregated_data_list = list(aggregated_data.items())
   
    paginator = Paginator(aggregated_data_list, 10)
    page_number = request.GET.get('page')   
    page_obj = paginator.get_page(page_number)

    form = vehicleSummaryReportForm()
    context = {
        'page_obj': page_obj,
        'form': form,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'number_of_days': number_of_days,
        'vehicle_reg_number': vehicle_reg_number
    }
    return render(request, 'fleetmanagement/vehicle_payment_grand_sum.html', context)





@login_required
def management_summary_report(request):
    form = vehicleSummaryReportForm(request.GET or {'days': 20})
    vehicle_data = TransportUsage.objects.all()
    fuel_refill_data = FuelRefill.objects.all()
    vehicle_fault = Vehiclefault.objects.all()

    month_number = None
    month_name = None
    year = None
    vehicle_number=None
    start_date=None
    end_date=None

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        days = form.cleaned_data.get('days')
        vehicle_number = form.cleaned_data.get('vehicle_number')   
        year = form.cleaned_data.get("year")   
        month_name = form.cleaned_data.get("month")  
        if month_name:          
            month_number = datetime.strptime(month_name, "%B").month  # Converts "January" to 1 

        if start_date and end_date:
            vehicle_data = vehicle_data.filter(created_at__range=(start_date, end_date))
            fuel_refill_data = fuel_refill_data.filter(created_at__range=(start_date, end_date))
            vehicle_fault = vehicle_fault.filter(created_at__range=(start_date, end_date))
        elif days:
            end_date = datetime.today()
            start_date = end_date - timedelta(days=days)
            vehicle_data = vehicle_data.filter(created_at__range=(start_date, end_date))
            fuel_refill_data = fuel_refill_data.filter(created_at__range=(start_date, end_date))
            vehicle_fault = vehicle_fault.filter(created_at__range=(start_date, end_date))


        elif vehicle_number:
            vehicle_data = vehicle_data.filter(booking__vehicle__vehicle_registration_number=vehicle_number)
            vehicle_fault = vehicle_fault.filter(vehicle__vehicle_registration_number=vehicle_number)
            fuel_refill_data = fuel_refill_data.filter(vehicle__vehicle_registration_number=vehicle_number)
        
        elif month_number:
            vehicle_data = vehicle_data.filter(created_at__month=month_number)
            vehicle_fault = vehicle_fault.filter(created_at__month=month_number)
            fuel_refill_data= fuel_refill_data.filter(created_at__month=month_number)
        elif year:
            vehicle_data = vehicle_data.filter(created_at__year=year)
            vehicle_fault = vehicle_fault.filter(created_at__year=year)
            fuel_refill_data= fuel_refill_data.filter(created_at__year=year)
           

        vehicle_data = vehicle_data.aggregate(
            total_fuel_consumed=Sum('fuel_consumed'),
            total_kilometer_run=Sum('kilometer_run'),
            day_end_kilometer_cost_CNG=Sum('kilometer_cost_CNG'),
            day_end_kilometer_cost_gasoline=Sum('kilometer_cost_gasoline'),
            total_kilometer_cost=Sum('kilometer_cost'),
            total_travel_days=Count('travel_date', distinct=True),
            total_vehicle_base_rent=Sum('booking__vehicle__vehicle_rent')/30,
        )

        if vehicle_data.get('total_kilometer_cost', 0) and vehicle_data.get('total_vehicle_base_rent', 0): 
            vehicle_data['total_vehicle_cost'] = (
                vehicle_data.get('total_kilometer_cost', 0) + vehicle_data.get('total_vehicle_base_rent', 0)
            )

        fuel_refill_data = fuel_refill_data.aggregate(
            total_refill_amount_pump=Sum('refill_amount', filter=Q(refill_type='pump')),
            total_refill_amount_local_purchase=Sum('refill_amount', filter=Q(refill_type='local_purchase')),
            total_refill_amount=Sum('refill_amount'),
            total_fuel_consumed_refill=Sum('vehicle_fuel_consumed'),
        )

        vehicle_fault = vehicle_fault.aggregate(
            fault_duration=Sum('fault_duration_hours'),
        )

        kilometer_run_per_litre = 0
        if vehicle_data['total_fuel_consumed']:
            kilometer_run_per_litre = vehicle_data['total_kilometer_run'] / vehicle_data['total_fuel_consumed']

        net_fuel_balance=0
        if fuel_refill_data.get('total_refill_amount', 0) and vehicle_data.get('total_fuel_consumed', 0):
            net_fuel_balance= fuel_refill_data.get('total_refill_amount', 0) - vehicle_data.get('total_fuel_consumed', 0)


        combined_data = {
            'fault_duration': vehicle_fault.get('fault_duration', 0),
            'total_refill_amount': fuel_refill_data.get('total_refill_amount', 0),
            'total_refill_amount_pump': fuel_refill_data.get('total_refill_amount_pump', 0),
            'total_refill_amount_local_purchase': fuel_refill_data.get('total_refill_amount_local_purchase', 0),
            'total_fuel_consumed_refill': fuel_refill_data.get('total_fuel_consumed_refill', 0),
            'total_fuel_consumed': vehicle_data.get('total_fuel_consumed', 0),
            'net_fuel_balance': net_fuel_balance,
            'total_kilometer_run': vehicle_data.get('total_kilometer_run', 0),
            'day_end_kilometer_cost_CNG': vehicle_data.get('day_end_kilometer_cost_CNG', 0),
            'day_end_kilometer_cost_gasoline': vehicle_data.get('day_end_kilometer_cost_gasoline', 0),
            'total_kilometer_cost': vehicle_data.get('total_kilometer_cost', 0),
            'total_travel_days': vehicle_data.get('total_travel_days', 0),
            'total_vehicle_base_rent': vehicle_data.get('total_vehicle_base_rent', 0),
            'total_vehicle_cost': vehicle_data.get('total_vehicle_cost', 0),
            'kilometer_run_per_litre': kilometer_run_per_litre,
        }

        total_kilometer_run = 0
        total_kilometer_cost = 0
        total_vehicle_base_rent= 0

        if vehicle_data.get('total_kilometer_run', 0) :
            total_kilometer_run = vehicle_data.get('total_kilometer_run', 0) 
        if vehicle_data.get('total_kilometer_cost', 0):
            total_kilometer_cost = vehicle_data.get('total_kilometer_cost', 0)
        if vehicle_data.get('total_vehicle_base_rent', 0):
            total_vehicle_base_rent = vehicle_data.get('total_vehicle_base_rent', 0)
      

        chart_data = {
            'labels': [
            
                'total kilometer run',
                'total kilometer cost',
                'total vehicle rent',
            
            ],
            'values': [
            
                float(total_kilometer_run),                       
                float(total_kilometer_cost),
                float(total_vehicle_base_rent),   
            ],
        }
    else:
        form = vehicleSummaryReportForm()  
    form = vehicleSummaryReportForm()
    return render(request, 'fleetmanagement/management_report.html', {
        'data': combined_data,
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
        'month_name': month_name,
        'year': year,
        'vehicle_number': vehicle_number,
        'chart_data':json.dumps(chart_data)
    })
