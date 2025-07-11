
from django.urls import path
from .import views


app_name = 'sales'


urlpatterns = [    
    
  path('sale_dashboard/', views.sale_dashboard, name='sale_dashboard'),

  path('create_sale_request/', views.create_sale_request, name='create_sale_request'),
  path('cconfirm_sale_request/', views.confirm_sale_request, name='confirm_sale_request'),
  path('process-sale-request/<int:order_id>/', views.process_sale_request, name='process_sale_request'),
  path('sale_request_order_list/', views.sale_request_order_list, name='sale_request_order_list'),   
  path('sale_request_items/<int:order_id>/', views.sale_request_items, name='sale_request_items'),

  path('create_sale_order/<int:request_id>/', views.create_sale_order, name='create_sale_order'),
  path('confirm_sale_order/', views.confirm_sale_order, name='confirm_sale_order'),
  path('process-sale-order/<int:order_id>/', views.process_sale_order, name='process_sale_order'),
  path('sale_order_list/', views.sale_order_list, name='sale_order_list'),
  path('sale_order_list_report/', views.sale_order_list_report, name='sale_order_list_report'),
 

  path('qc_dashboard/', views.qc_dashboard, name='qc_dashboard'),
  path('qc_dashboard/<int:sale_order_id>/', views.qc_dashboard, name='qc_dashboard_with_order'), 
  path('qc_inspect_item/<int:item_id>/', views.qc_inspect_item, name='qc_inspect_item'),


  path('sale_order_item/', views.sale_order_item, name='sale_order_item'),
  path('sale_order_items/<int:order_id>/', views.sale_order_items, name='sale_order_items'),
  path('sale_order_item_dispatch/<str:order_id>/', views.sale_order_item_dispatch, name='sale_order_item_dispatch'),
  path('update_sale_order_status/<int:order_id>/', views.update_sale_order_status, name='update_sale_order_status'),

 path('product_sales_report/', views.product_sales_report, name='product_sales_report'),


]
