
from django.urls import path
from .import views


app_name = 'repairreturn'



urlpatterns = [  
    
  path('create_return_request/<int:sale_order_id>/', views.create_return_request, name='create_return_request'),
  path('return_request_progress/<int:sale_order_id>/', views.return_request_progress, name='return_request_progress'),
  path('return_request_list/', views.return_request_list, name='return_request_list'),
  path('manage_return_request/<int:return_id>/', views.manage_return_request, name='manage_return_request'),
  path('faulty_product_list/', views.faulty_product_list, name='faulty_product_list'),
  path('repair_faulty_product/<int:faulty_product_id>/', views.repair_faulty_product, name='repair_faulty_product'),
  path('return_repaired_product/<int:faulty_product_id>/', views.replacement_return_repaired_product, name='return_repaired_product'),

  path('replacement_product_list/', views.replacement_product_list, name='replacement_product_list'),
  path('sale_order_list/', views.sale_order_list, name='sale_order_list'),
  path('return_dashboard/', views.repair_return_dashboard, name='return_dashboard'),


  path('create_scrap_request/', views.create_scrap_request, name='create_scrap_request'),
  path('confirm_scrap_request/', views.confirm_scrap_request, name='confirm_scrap_request'),
  path('scrap_order_list/', views.scrap_order_list, name='scrap_order_list'),
   path('scrap_request_items/<int:order_id>/', views.scrap_request_items, name='scrap_request_items'),
  path('process_scrap_order/<int:order_id>/', views.process_scrap_order, name='process_scrap_order'),
  path('scrap_confirmation/<int:order_id>/', views.scrap_confirmation, name='scrap_confirmation'),


]

