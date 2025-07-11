from django.contrib import admin

from .models import Inventory,InventoryTransaction,Warehouse,Location,TransferItem,TransferOrder

admin.site.register(Inventory)
admin.site.register(InventoryTransaction)
admin.site.register(Warehouse)
admin.site.register(Location)

admin.site.register(TransferOrder)
admin.site.register(TransferItem)
