from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from product.models import Product
from purchase.models import Batch
from accounts.models import CustomUser
from decimal import Decimal
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, DecimalField
from supplier.models import Supplier




class Purchase(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="purchase_warehouse")
    invoice_no = models.CharField(max_length=50, blank=True)
    purchase_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate invoice_no if missing
        if not self.invoice_no:
            today_str = timezone.now().strftime("%Y%m%d")
            last_purchase = Purchase.objects.filter(invoice_no__startswith=today_str).order_by('id').last()
            seq = int(last_purchase.invoice_no.split("-")[-1]) + 1 if last_purchase and last_purchase.invoice_no else 1
            self.invoice_no = f"{today_str}-{seq:03d}"

        super().save(*args, **kwargs)

        # After saving, update total_amount and vat_amount from related items
        total_amount = self.purchase_items.aggregate(
            total=Coalesce(Sum(F('quantity') * F('unit_price'), output_field=DecimalField()), Decimal('0.00'))
        )['total']

        total_vat = self.purchase_items.aggregate(
            total=Coalesce(Sum(F('vat_amount'), output_field=DecimalField()), Decimal('0.00'))
        )['total']

        # Only update if changed to avoid recursion
        if self.total_amount != total_amount or self.vat_amount != total_vat:
            Purchase.objects.filter(id=self.id).update(total_amount=total_amount, vat_amount=total_vat)

    def __str__(self):
        return f"Purchase #{self.invoice_no}"



class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="purchase_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="purchase_products", blank=True, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shelf = models.ForeignKey("inventory.Shelf", on_delete=models.SET_NULL, blank=True, null=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def save(self, *args, **kwargs):       
        self.total_price = self.unit_price * self.quantity
        self.vat_amount = (self.total_price * self.vat_percentage) / Decimal('100')
        super().save(*args, **kwargs)

        self.purchase.save()
      

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
