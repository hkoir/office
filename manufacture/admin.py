from django.contrib import admin

from.models import ReceiveFinishedGoods,MaterialsRequestItem,MaterialsRequestOrder,MaterialsDeliveryItem
from.models import FinishedGoodsReadyFromProduction,ManufactureQualityControl

admin.site.register(ReceiveFinishedGoods)
admin.site.register(MaterialsDeliveryItem)
admin.site.register(MaterialsRequestItem)

admin.site.register(FinishedGoodsReadyFromProduction)
admin.site.register(ManufactureQualityControl)
admin.site.register(MaterialsRequestOrder)
