
from django.urls import path
from .import views
from .views import mark_notification_read_view

app_name = 'reporting'



urlpatterns = [
    
  path('report_dashboard/', views.report_dashboard, name='report_dashboard'),
  path('notification/read/<int:notification_id>/', mark_notification_read_view, name='mark_notification_read'),
  path('notification_list/', views.notification_list, name='notification_list'),
  
  path('product_list/', views.product_list, name='product_list'),
  path('batchwise_product_status/', views.batchwise_product_status, name='batchwise_product_status'),
  path("get-batch-warehouse-data/", views.get_batch_warehouse_data, name="get_batch_warehouse_data"),
  path('product_report/<int:product_id>/', views.product_report, name='product_report'),
  path('', views.warehouse_report, name='warehouse_report'),

  path('generate_sale_challan/<int:order_id>/', views.generate_sale_challan, name='generate_sale_challan'),
  path('download_sale_delivery_orders/<int:order_id>/', views.download_sale_delivery_order_csv, name='download_sale_delivery_orders'),

  path('generate_purchase_challan/<int:order_id>/', views.generate_purchase_challan, name='generate_purchase_challan'),
  path('download_purchase_delivery_orders/<int:order_id>/', views.download_purchase_delivery_order_csv, name='download_purchase_delivery_orders'),

 path('inventory-status/', views.monitor_inventory_status, name='monitor_inventory_status'),
 path('archive_old_notifications/', views.archive_old_notifications, name='archive_old_notifications'),
 path('Calculate_sales_profit/', views.Calculate_sales_profit, name='Calculate_sales_profit'),

  path('calculate_product_wise_revenue/', views.calculate_product_wise_revenue, name='calculate_product_wise_revenue'),


]
