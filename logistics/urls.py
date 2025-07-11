
from django.urls import path
from .import views


app_name = 'logistics'


urlpatterns = [
    path('create_purchase_shipment/<int:purchase_order_id>/', views.create_purchase_shipment, name='create_purchase_shipment'),
    path('purchase_shipment_list/', views.purchase_shipment_list, name='purchase_shipment_list'),
    path('purchase_shipment_detail/<int:shipment_id>/', views.purchase_shipment_detail, name='purchase_shipment_detail'),   
    path('create_purchase_dispatch_item/<int:dispatch_id>/', views.create_purchase_dispatch_item, name='create_purchase_dispatch_item'),   
    path('confirm_purchase_dispatch_item/', views.confirm_purchase_dispatch_item, name='confirm_purchase_dispatch_item'),

    path('order/<int:purchase_order_id>/dispatch-items/', views.dispatch_item_list, name='dispatch_item_list'),
    path('dispatch-item/<int:dispatch_item_id>/update-status/', views.update_dispatch_status, name='update_dispatch_status'),
    path('cancel_dispatch_item<int:dispatch_item_id>/', views.cancel_dispatch_item, name='cancel_dispatch_item'),

######################################################################################################
    
    path('create_sale_shipment/<int:sale_order_id>/', views.create_sale_shipment, name='create_sale_shipment'),
    path('sale_shipment_list/', views.sale_shipment_list, name='sale_shipment_list'),
    path('sale_shipment_detail/<int:shipment_id>/', views.sale_shipment_detail, name='sale_shipment_detail'),
    path('create_sale_dispatch_item/<int:dispatch_id>/', views.create_sale_dispatch_item, name='create_sale_dispatch_item'),   
    path('confirm_sale_dispatch_item/', views.confirm_sale_dispatch_item, name='confirm_sale_dispatch_item'),

    path('sale-order/<int:sale_order_id>/dispatch-items/', views.sale_dispatch_item_list, name='sale_dispatch_item_list'),
    path('sale-dispatch-item/<int:dispatch_item_id>/update-status/', views.update_sale_dispatch_status, name='update_sale_dispatch_status'),
    path('cancel_sale_dispatch_item/<int:dispatch_item_id>/', views.cancel_sale_dispatch_item, name='cancel_sale_dispatch_item')

    
    
]

