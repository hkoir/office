from django.contrib import admin

from.models import SaleRequestOrder,SaleRequestItem,SaleOrder,SaleOrderItem,SaleQualityControl

admin.site.register(SaleRequestOrder)
admin.site.register(SaleRequestItem)
admin.site.register(SaleOrder)
admin.site.register(SaleOrderItem)

admin.site.register(SaleQualityControl)
