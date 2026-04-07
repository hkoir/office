
from django.urls import path
from .import views


app_name = 'finance'



urlpatterns = [
    path('create_purchase_invoice/<int:order_id>/', views.create_purchase_invoice, name='create_purchase_invoice'),
    path('create_purchase_invoice_from_quotation/<int:quotation_id>/', views.create_purchase_invoice_from_quotation, name='create_purchase_invoice_from_quotation'),
    path('create_purchase_invoice_from_purchase_order/<int:po_id>/', views.create_purchase_invoice_from_purchase_order, name='create_purchase_invoice_from_purchase_order'),
    path('create_purchase_payment/<int:invoice_id>/', views.create_purchase_payment, name='create_purchase_payment'),
    path('purchase_invoice_list/', views.purchase_invoice_list, name='purchase_invoice_list'),
    path('purchase_invoice_detail/<int:invoice_id>/', views.purchase_invoice_detail, name='purchase_invoice_detail'),
    
    path('download_purchase_invoice/<int:purchase_order_id>/', views.download_purchase_invoice, name='download_purchase_invoice'),
    path('download_sale_invoice/<int:sale_order_id>/', views.download_sale_invoice, name='download_sale_invoice'),


    path('create_sale_invoice_from_sale_order/<int:so_id>/', views.create_sale_invoice_from_sale_order, name='create_sale_invoice_from_sale_order'),
    path('create_sale_invoice/<int:order_id>/', views.create_sale_invoice, name='create_sale_invoice'),
    path('create_sale_payment/<int:invoice_id>/', views.create_sale_payment, name='create_sale_payment'),
    path('sale_invoice_list/', views.sale_invoice_list, name='sale_invoice_list'),    
    path('sale_invoice_detail/<int:invoice_id>/', views.sale_invoice_detail, name='sale_invoice_detail'),

   path('add_purchase_invoice_attachement/<int:invoice_id>/', views.add_purchase_invoice_attachment, name='add_purchase_invoice_attachment'),
   path('add_purchase_payment_attachement/<int:invoice_id>/', views.add_purchase_payment_attachment, name='add_purchase_payment_attachment'),
   path('add_sale_invoice_attachement/<int:invoice_id>/', views.add_sale_invoice_attachment, name='add_sale_invoice_attachment'),
   path('add_sale_payment_attachement/<int:invoice_id>/', views.add_sale_payment_attachment, name='add_sale_payment_attachment'),


    path('create_direct_invoice/', views.create_direct_invoice, name='create_direct_invoice'),
    path('update_direct_invoice/<int:pk>/', views.create_direct_invoice, name='update_direct_invoice'),
    path('confirm_direct_invoice/<int:invoice_id>/', views.confirm_or_update_direct_invoice, name='confirm_direct_invoice'),
    path('direct_invoices/', views.direct_invoice_list, name='direct_invoice_list'),
    path('direct_invoices/<int:pk>/', views.direct_invoice_detail, name='direct_invoice_detail'),
    path('direct_invoice/<int:pk>/mark_paid/', views.mark_invoice_paid, name='mark_direct_invoice_paid'),
         

    path("create_direct_purchase_invoice/", views.create_direct_purchase_invoice, name="create_direct_purchase_invoice"),
    path("update_direct_purchase_invoice/<int:pk>/", views.create_direct_purchase_invoice, name="update_direct_purchase_invoice"),
    path('confirm_purchase_direct_invoice/<int:invoice_id>/', views.confirm_or_update_direct_purchase_invoice, name='confirm_direct_purchase_invoice'),
    path('direct_purchase_invoices/', views.direct_purchase_invoice_list, name='direct_purchase_invoice_list'),
    path('direct_purchase_invoices/<int:pk>/', views.direct_purchase_invoice_detail, name='direct_purchase_invoice_detail'),
    path('direct_purchase_invoice/<int:pk>/mark_paid/', views.mark_direct_purchase_invoice_paid, name='mark_direct_purchase_invoice_paid'),

 


]