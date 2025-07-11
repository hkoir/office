from django.contrib import admin


from.models import ExistingOrder,ExistingOrderItems,OperationsRequestOrder,OperationsRequestItem,OperationsDeliveryItem

admin.site.register(ExistingOrder)
admin.site.register(ExistingOrderItems)
admin.site.register(OperationsRequestOrder)
admin.site.register(OperationsRequestItem)
admin.site.register(OperationsDeliveryItem)
