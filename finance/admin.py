from django.contrib import admin

from.models import PurchaseInvoice,PurchasePayment,SaleInvoice,SalePayment
from.models import PurchaseInvoiceAttachment,PurchasePaymentAttachment,SaleInvoiceAttachment,SalePaymentAttachment

admin.site.register(PurchaseInvoice)
admin.site.register(PurchasePayment)
admin.site.register(SaleInvoice)
admin.site.register(SalePayment)

admin.site.register(PurchaseInvoiceAttachment)
admin.site.register(PurchasePaymentAttachment)
admin.site.register(SaleInvoiceAttachment)
admin.site.register(SalePaymentAttachment)
