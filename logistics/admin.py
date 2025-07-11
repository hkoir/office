from django.contrib import admin

from.models import SaleShipment,PurchaseShipment,PurchaseDispatchItem,SaleDispatchItem


admin.site.register(SaleShipment)
admin.site.register(PurchaseShipment)
admin.site.register(PurchaseDispatchItem)
admin.site.register(SaleDispatchItem)