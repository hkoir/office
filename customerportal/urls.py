
from django.urls import path
from .import views
from sales.views import sale_order_list

app_name = 'customerportal'


urlpatterns = [
    path('', views.partner_landing_page, name='partner_landing_page'),  
    path('public_landing_page/', views.public_landing_page, name='public_landing_page'),
    path('job_landing_page/', views.job_landing_page, name='job_landing_page'),        
   
    path('create_ticket/',views.create_ticket, name='create_ticket'),
    path('ticket_list/',views.ticket_list, name='ticket_list'),
    path('update_ticket/<int:ticket_id>/',views.update_ticket, name='update_ticket'),

    path('sale_order_list/',views.sale_order_list, name='sale_order_list'),
    path('sale-order/<int:sale_order_id>/dispatch-items/', views.sale_dispatch_item_list, name='sale_dispatch_item_list'),
    path('sale-dispatch-item/<int:dispatch_item_id>/update-status/', views.update_sale_dispatch_status, name='update_sale_dispatch_status'),
    path('sale-order/<int:sale_order_id>/item_dispatched/', views.item_dispatched, name='item_dispatched'),

    path('customer_qc_dashboard/', views.customer_qc_dashboard, name='customer_qc_dashboard'),
    path('customer_qc_dashboard/<int:sale_order_id>/', views.customer_qc_dashboard, name='customer_qc_dashboard_with_order'), 
    path('customer_qc_inspect_item/<int:item_id>/', views.customer_qc_inspect_item, name='customer_qc_inspect_item'),


    path('create_return_request/<int:sale_order_id>/', views.create_return_request, name='create_return_request'),
    path('return_request_progress/<int:sale_order_id>/', views.return_request_progress, name='return_request_progress'),
    path('return_request_list/', views.customer_return_request_list, name='return_request_list'),
    path('customer_feedback/<int:return_id>/', views.repair_return_customer_feedback, name='customer_feedback'),
    path('ticket_customer_feedback/<int:ticket_id>/', views.ticket_customer_feedback, name='ticket_customer_feedback'),
   

    path('purchase_order_list/', views.purchase_order_list, name='purchase_order_list'),        
    path('purchase_order_items/<int:order_id>/', views.purchase_order_items, name='purchase_order_items'),      
    path('order/<int:purchase_order_id>/dispatch-items/', views.dispatch_item_list, name='dispatch_item_list'),
    path('dispatch-item/<int:dispatch_item_id>/update-status/', views.update_dispatch_status, name='update_dispatch_status'),
    path('create_purchase_invoice/<int:order_id>/', views.create_purchase_invoice, name='create_purchase_invoice'),
    path('add_purchase_invoice_attachement/<int:invoice_id>/', views.add_purchase_invoice_attachment, name='add_purchase_invoice_attachment'),


   
    path('job_list_candidate_view/', views.job_list_candidate_view, name='job_list_candidate_view'),   
    path('job_application/<int:id>/', views.job_application, name='job_application'),
    path('pre_exams/<int:exam_id>/take/<int:candidate_id>/', views.pre_take_exam, name='pre_take_exam'),
    path('exams/<int:exam_id>/take/<int:candidate_id>/', views.take_exam, name='take_exam'),

    path('candidate_confirmation/<int:candidate_id>/', views.candidate_confirmation, name='candidate_confirmation'),
    path("congratulations/<int:candidate_id>/", views.congratulations, name="congratulations"),
    path('candidate_joining/<int:candidate_id>/', views.candidate_joining, name='candidate_joining'),
   
    path('selected_candidate_job_status/', views.selected_candidate_job_status, name='selected_candidate_job_status'), 

    path('search_applications/', views.search_applications, name='search_applications'),   
    path('position_details/<int:id>/', views.position_details, name='position_details'), 

    path('preview_offer_letter/<int:candidate_id>/', views.preview_offer_letter, name='preview_offer_letter'), 

       
 

]
