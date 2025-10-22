
from django.urls import path
from .import views


app_name = 'operations'

urlpatterns = [   

  path('operations_dashboard/', views.operations_dashboard, name='operations_dashboard'),
 
  path('add_existing_items/', views.add_existing_items, name='add_existing_items'),
  path('confirm_add_existing_items/', views.confirm_add_existing_items, name='confirm_add_existing_items'),
  path('existing_items_list/', views.existing_items_list, name='existing_items_list'),

  path('create_operations_items_request', views.create_operations_items_request, name='create_operations_items_request'),
  path('confirm_operations_items_request/', views.confirm_operations_items_request, name='confirm_operations_items_request'), 
  path('operations_request_order_list/', views.operation_request_order_list, name='operations_request_order_list'),
  path('operations_request_order_items<int:order_id>//', views.operation_request_order_items, name='operations_request_order_items'),

  path('create_operations_items_delivery/<int:request_id>/', views.create_operations_items_delivery, name='create_operations_items_delivery'),
  path('confirm_operations_items_delivery/', views.confirm_operations_items_delivery, name='confirm_operations_items_delivery'),
]
