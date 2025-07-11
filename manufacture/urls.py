
from django.urls import path
from .import views


app_name = 'manufacture'


urlpatterns = [    
    
  path('manufacture_dashboard/', views.manufacture_dashboard, name='manufacture_dashboard'),
  
  path('create_materials_request/', views.create_materials_request, name='create_materials_request'),
  path('cconfirm_materials_request/', views.confirm_materials_request, name='confirm_materials_request'),
  
  path('materials_request_order_list/', views.materiala_request_order_list, name='materials_request_order_list'),
  path('materials_request_items/<int:order_id>/', views.materials_request_items, name='materials_request_items'),
  path('process_materials_request/<int:order_id>/', views.process_materials_request, name='process_materials_request'),
 
  path('materials_order_item/', views.materials_order_item, name='materials_order_item'),
  

  path('create_materials_delivery/<int:request_id>/', views.create_materials_delivery, name='create_materials_delivery'),
  path('confirm_materials_delivery/', views.confirm_materilas_delivery, name='confirm_materials_delivery'),
  path('materials_delivered_items/<int:order_id>/', views.materials_delivered_items, name='materials_delivered_items'),

  path('submit-finished-goods/<int:request_id>/', views.submit_finished_goods, name='submit_finished_goods'),
   path('direct_submit-finished-goods/', views.direct_submit_finished_goods, name='direct_submit_finished_goods'),
  
  path('qc_dashboard/', views.qc_dashboard, name='qc_dashboard'),
  path('qc_dashboard/<int:purchase_order_id>/', views.qc_dashboard, name='qc_dashboard_with_order'), 
  path('qc_inspect_item/<int:item_id>/', views.qc_inspect_item, name='qc_inspect_item'),


 
 

]
