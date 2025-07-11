
from django.urls import path
from .import views


app_name = 'officemanagement'


urlpatterns = [

    ##################### Office supplies and Stationary #########################

    path('create_category/', views.manage_category, name='create_category'),
    path('update_category/<int:id>/', views.manage_category, name='update_category'),
    path('delete_category/<int:id>/', views.delete_category, name='delete_category'),

    path('create_product/', views.manage_product, name='create_product'),
    path('update_product/<int:id>/', views.manage_product, name='update_product'),
    path('delete_product/<int:id>/', views.delete_product, name='delete_product'),

    path('create_batch/', views.manage_batch, name='create_batch'),
    path('update_batch/<int:id>/', views.manage_batch, name='update_batch'),
    path('delete_batch/<int:id>/', views.delete_batch, name='delete_batch'),

    path('create_purchase_request/', views.create_purchase_request, name='create_purchase_request'),
    path('confirm_purchase_request/', views.confirm_purchase_request, name='confirm_purchase_request'),
    path('purchase_request_list/', views.purchase_request_list, name='purchase_request_list'),
    path('add_invoice/<int:request_id>/', views.add_invoice, name='add_invoice'),
    path('items_requested/<int:request_id>/', views.items_requested, name='items_requested'),
   
    path('process_purchase_request/<int:order_id>/', views.process_purchase_request, name='process_purchase_request'),
    path('purchase_confirmation_and_warehouse_entry/<int:order_id>/', views.purchase_confirmation_and_warehouse_entry, name='purchase_confirmation_and_warehouse_entry'),

    path('create_usage_request/', views.create_usage_request, name='create_usage_request'),
    path('confirm_usage_request/', views.confirm_usage_request, name='confirm_usage_request'),
    path('usage_request_list/', views.usage_request_list, name='usage_request_list'),
    path('usage_items_requested/<int:request_id>/', views.usage_items_requested, name='usage_items_requested'),

    path('process_usage_request/<int:request_id>/', views.process_usage_request, name='process_usage_request'),
    path('confirm_usage_dispatch/<int:request_id>/', views.confirm_usage_dispatch, name='confirm_usage_dispatch'),
  

   ##################### Meeting room #########################

    path('create_meeting_room/', views.manage_meeting_room, name='create_meeting_room'),
    path('update_meeting_room/<int:id>/', views.manage_meeting_room, name='update_meeting_room'),
    path('delete_meeting_room/<int:id>/', views.delete_meeting_room, name='delete_meeting_room'),
   
    path('create_meeting_order/', views.manage_meeting_order, name='create_meeting_order'),
    path('update_meeting_order/<int:id>/', views.manage_meeting_order, name='update_meeting_order'),
    path('delete_meeting_order/<int:id>/', views.delete_meeting_order, name='delete_meeting_order'),

 
    path('create_attendee/', views.manage_attendee, name='create_attendee'),
    path('update_attendee/<int:id>/', views.manage_attendee, name='update_attendee'),
    path('delete_attendee/<int:id>/', views.delete_attendee, name='delete_attendee'),


    path("meeting-rooms/", views.meeting_room_list, name="meeting_room_list"),
    path("meeting-rooms/<int:room_id>/calendar/", views.meeting_room_calendar, name="meeting_room_calendar"),
    path("meeting-rooms/<int:room_id>/book/", views.book_meeting_room, name="book_meeting_room"),
  
  ##################### IT support Ticketing #########################

    path('create_IT_support/', views.manage_IT_support, name='create_IT_support'),
    path('update_IT_support/<int:id>/', views.manage_IT_support, name='update_IT_support'),
    path('delete_IT_support/<int:id>/', views.delete_IT_support, name='delete_IT_support'),
    path('IT_support_list/', views.IT_support_list, name='IT_support_list'),
    path('update_it_feedback/<int:support_id>/', views.update_it_feedback, name='update_it_feedback'),

  ##################### Visitor management #########################

    path('create_visitor_group/', views.manage_visitor_group, name='create_visitor_group'),
    path('update_visitor_group/<int:id>/', views.manage_visitor_group, name='update_visitor_group'),
    path('delete_visitor_group/<int:id>/', views.delete_visitor_group, name='delete_visitor_group'),

    path('create_visitor_member/', views.add_member_visitor_group, name='create_visitor_member'),
    path('update_visitor_member/<int:id>/', views.add_member_visitor_group, name='update_visitor_member'),
    path('delete_visitor_member/<int:id>/', views.delete_member_visitor_group, name='delete_visitor_member'),
    path('search_visitor/', views.search_visitor, name='search_visitor'),

  ##################### office expense advance #########################
    path('create_expense_advance/', views.manage_expense_advance, name='create_expense_advance'),
    path('update_expense_advance/<int:id>/', views.manage_expense_advance, name='update_expense_advance'),
    path('delete_expense_advance/<int:id>/', views.delete_expense_advance, name='delete_expense_advance'),
    path('expense_advance_list/', views.expense_advance_list, name='expense_advance_list'),   
    path('expense_advance_approval/<int:submission_id>/', views.expense_advance_approval, name='expense_advance_approval'), 


    path('create_expense_order/', views.manage_expense_order, name='create_expense_order'),
    path('update_expense_order/<int:id>/', views.manage_expense_order, name='update_expense_order'),
    path('delete_expense_order/<int:id>/', views.delete_expense_order, name='delete_expense_order'),

    path('create_expense_item/', views.manage_expense_item, name='create_expense_item'),
    path('update_expense_item/<int:id>/', views.manage_expense_item, name='update_expense_item'),
    path('delete_expense_item/<int:id>/', views.delete_expense_item, name='delete_expense_item'),
    
    path('expense_order_list/', views.expense_order_list, name='expense_order_list'),
    path('items_submitted/<int:submission_id>/', views.items_submitted, name='items_submitted'),
    path('expense_approval/<int:submission_id>/', views.expense_approval, name='expense_approval'),

   ##################### Documentations #########################
    path('create_office_document/', views.manage_office_document, name='create_office_document'),
    path('update_office_document/<int:id>/', views.manage_office_document, name='update_office_document'),
    path('delete_office_document/<int:id>/', views.delete_office_document, name='delete_office_document'),
    path('office_document_list/', views.office_document_list, name='office_document_list'),

    ##################### Report #########################
    path('inventory_report/', views.inventory_report, name='inventory_report'),
    path('visitor_reports/', views.visitor_reports, name='visitor_reports'),
    path('meeting_room_report/', views.meeting_room_report, name='meeting_room_report'),
    path('advance_reconcilation_report/', views.advance_reconciliation_report, name='advance_reconcilation_report'),
    path('top_expense_categories/', views.top_expense_categories, name='top_expense_categories'),


  ##################### Dashboard #########################
    path('office_supplies_stationary/', views.office_supplies_stationary, name='office_supplies_stationary'),
    path('office_expense_advance/', views.office_expense_advance, name='office_expense_advance'),
    path('office_meeting_room_booking/', views.office_meeting_room_booking, name='office_meeting_room_booking'),
    path('office_it_support_ticket/', views.office_it_support_ticket, name='office_it_support_ticket'),
    path('office_visitor_management/', views.office_visitor_management, name='office_visitor_management'),
    path('office_documentations/', views.office_documentations, name='office_documentations'),
  



] 
