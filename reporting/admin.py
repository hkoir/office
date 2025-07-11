from django.contrib import admin

from.models import Notification,InventoryReport,SaleShipmentReport,PurchaseShipmentReport

admin.site.register(Notification)
admin.site.register(InventoryReport)
admin.site.register(SaleShipmentReport)
admin.site.register(PurchaseShipmentReport)
