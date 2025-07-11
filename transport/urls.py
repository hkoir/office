
from django.urls import path
from .import views


app_name = 'transport'


urlpatterns = [
    path('transport_dashboard/', views.transport_dashboard, name='transport_dashboard'),
    path('create_transport/', views.manage_transport, name='create_transport'),
    path('update_transport/<int:id>/', views.manage_transport, name='update_transport'),
    path('delete_transport/<int:id>/', views.delete_transport, name='delete_transport'),
   
    path('transport_details/<int:transport_id>/', views.transport_details, name='transport_details'),
    path('available_transports/', views.available_transports, name='available_transports'),  # View available transport
   
    path('create_transport_request/', views.create_transport_request, name='create_transport_request'),
    path('update_transport_request/<int:id>/', views.create_transport_request, name='update_transport_request'),  # Request transport
    path('delete_transport_request/<int:id>/', views.delete_transport_request, name='delete_transport_request'),  # Request transport
    path('create_transport_request_id/<int:id>/', views.create_transport_request_id, name='create_transport_request_id'),  # Request transport    
   
   
    path('request/<int:request_id>/approve/', views.transport_request_approval, name='transport_request_approval'),  # Approve request (manager)
    path('update_booking/<int:booking_id>/', views.update_booking, name='update_booking'),  # Approve request (manager)
   
    path('booking_history/', views.booking_history, name='booking_history'),  
    
    path('create_time_extension/<int:id>/', views.create_time_extension, name='create_time_extension'),    
    path('approve_time_extension/<int:id>/', views.approve_time_extension, name='approve_time_extension'), 


    path('transport_usage_update/<int:booking_id>/', views.transport_usage_update, name='transport_usage_update'),  
    path('penalty_history/', views.penalty_history, name='penalty_history'),
   
    path('create_fuel_refill/', views.manage_fuel_refill, name='create_fuel_refill'),  
    path('update_fuel_refill/<int:id>/', views.manage_fuel_refill, name='update_fuel_refill'),  
  
    path('create_vehicle_fault/', views.create_vehicle_fault, name='create_vehicle_fault'),   
    path('update_vehicle_fault/<int:id>/', views.create_vehicle_fault, name='update_vehicle_fault'),

    path('create_fuel_pump_database/', views.manage_fuel_pump, name='create_fuel_pump_database'),
    path('update_fuel_pump_database/<int:id>/', views.manage_fuel_pump, name='update_fuel_pump_database'),
    path('delete_fuel_pump/<int:id>/', views.delete_fuel_pump, name='delete_fuel_pump'), 
        
    
    path('create_vehicle_payment/', views.create_vehicle_payment, name='create_vehicle_payment'),
    path('update_vehicle_payment/<int:id>/', views.create_vehicle_payment, name='update_vehicle_payment'),
    path('delete_vehicle_payment/<int:id>/', views.delete_vehicle_payment, name='delete_vehicle_payment'),

    path('create_fuel_pump_payment/', views.create_fuel_pump_payment, name='create_fuel_pump_payment'),  
    path('update_fuel_pump_payment/<int:id>/', views.create_fuel_pump_payment, name='update_fuel_pump_payment'), 
    path('delete_fuel_pump_payment/<int:id>', views.delete_fuel_pump_payment, name='delete_fuel_pump_payment'), 
  
    path('fuel_by_pump/', views.fuel_by_pump, name='fuel_by_pump'),   
    path('datewise_fuel_withdraw/', views.datewise_fuel_withdraw, name='datewise_fuel_withdraw'),  
   
    path('vehicle_overtime_calc/', views.vehicle_overtime_calc, name='vehicle_overtime_calc'),
    path('vehicle_grand_summary/', views.vehicle_grand_summary, name='vehicle_grand_summary'),
    path('management_summary_report/', views. management_summary_report, name='management_summary_report'),
  
    path('refresh-status/', views.refresh_status, name='refresh_status'),

    path('vehicle_booking_calendar/<int:id>/', views.vehicle_booking_calendar, name='vehicle_booking_calendar'),
    path('penalty_payment/<int:penalty_id>/', views.penalty_payment, name='penalty_payment'),

   ]
