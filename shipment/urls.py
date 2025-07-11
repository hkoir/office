
from django.urls import path
from .import views


app_name = 'shipment'


urlpatterns = [
 path('update_shipment_tracking/<int:shipment_id>/', views.update_shipment_tracking, name='update_shipment_tracking'),
path('update_sale_shipment_tracking/<int:shipment_id>/', views.update_sale_shipment_tracking, name='update_sale_shipment_tracking'),
]
