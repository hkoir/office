
from django.urls import path
from .import views


app_name = 'inventory'


urlpatterns = [
    
    path('inventory_dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    path('create_warehouse/', views.manage_warehouse, name='create_warehouse'),
    path('update_warehouse/<int:id>/', views.manage_warehouse, name='update_warehouse'),
    path('delete_warehouse/<int:id>/', views.delete_warehouse, name='delete_warehouse'),

    path('create_location/', views.manage_location, name='create_location'),
    path('update_location/<int:id>/', views.manage_location, name='update_location'),
    path('delete_location/<int:id>/', views.delete_location, name='delete_location'),

    path('get_locations/', views.get_locations, name='get_locations'), 
    path('complete_quality_control/<int:qc_id>/', views.complete_quality_control, name='complete_quality_control'),    
   # path('complete_sale_quality_control/<int:qc_id>/', views.complete_sale_quality_control, name='complete_sale_quality_control'),

 
    path('inventory_list/', views.inventory_list, name='inventory_list'),
    path('inventory_aggregate_list/', views.inventory_aggregate_list, name='inventory_aggregate_list'),
    path('inventory_executive_sum/', views.inventory_executive_sum, name='inventory_executive_sum'),
    
    path('complete_manufacture_quality_control/<int:qc_id>/', views.complete_manufacture_quality_control, name='complete_manufacture_quality_control'),


  path('create_transfer/', views.create_transfer, name='create_transfer'),
  path('confirm_transfer/', views.confirm_transfer, name='confirm_transfer'),
  path('transfer_order_list/', views.transfer_order_list, name='transfer_order_list'),
  path('transfer_order_detail/<int:transfer_order_id>/', views.transfer_order_detail, name='transfer_order_detail'),


 path('inventory_transaction_report/', views.inventory_transaction_report, name='inventory_transaction_report'),

 path('create_warehouse_reorder_level/', views.manage_warehouse_reorder_level, name='create_warehouse_reorder_level'),
 path('update_warehouse_reorder_level/<int:id>/', views.manage_warehouse_reorder_level, name='update_warehouse_reorder_level'),
  path('delete_warehouse_reorder_level/', views.delete_warehouse_reorder_level, name='delete_warehouse_reorder_level'),
  
  
]
