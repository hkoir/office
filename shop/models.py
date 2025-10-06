from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from accounts.models import CustomUser
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
from datetime import datetime
from customer.models import Customer
from product.models import Category,Product
from purchase.models import Batch



  
class Sale(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.SET_NULL, null=True, blank=True)
    invoice_no = models.CharField(max_length=100,blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,related_name='customers')
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="sale_warehouse",null=True, blank=True)    
    sold_at = models.DateTimeField(default=timezone.now)
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.CharField(max_length=150, blank=True, null=True)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    ait_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)  

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            today_str = timezone.now().strftime("%Y%m%d")  # e.g., 20250829
            warehouse_name = self.warehouse.name if self.warehouse else "NOWAREHOUSE"

            last_sale = Sale.objects.filter(invoice_no__startswith=f"{warehouse_name}-{today_str}").order_by('id').last()

            if last_sale and last_sale.invoice_no:
                last_seq = int(last_sale.invoice_no.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1

            self.invoice_no = f"{warehouse_name}-{today_str}-{seq:03d}"

        super().save(*args, **kwargs)


    def __str__(self):
        return f"Invoice #{self.id}"

    @property
    def total_purchase_cost(self):
        return sum(item.quantity * item.batch.purchase_price for item in self.items.all())
    
    @property
    def total_sale_amount(self):
        return sum(item.total_price for item in self.items.all())

    def total_vat(self):
        return sum(item.vat_amount or 0 for item in self.items.all())

    def profit(self):
        return self.total_sale_amount() - self.total_purchase_cost()
  


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE,null=True,blank=True,related_name='sale_item_products')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    sold_at = models.DateTimeField(default=timezone.now) 
    is_exchange = models.BooleanField(default=False)    
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)  

    def save(self, *args, **kwargs):
        if not self.unit_price and self.batch.selling_price:
            self.unit_price = self.batch.selling_price 
        if self.total_price is None and self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        if self.vat_amount is None:
            vat_percent = self.batch.vat_percentage or Decimal('0')
            self.vat_amount = (self.total_price * vat_percent) / Decimal('100')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch.product.name} x {self.quantity}"




class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.CharField(max_length=150, blank=True, null=True)
    PAYMENT_METHODS = [
        ("cash","Cash"),
        ("card","Card"),
        ("bkash","bKash"),
        ("rocket","Rocket"),
    ]
    PAYMENT_STATUS = [
        ("pending","Pending"),
        ("completed","Completed"),
        ("success","Success"),
        ("cancelled","Cancelled"),
        ('refunded','Refunded'),
        ('exchanged','Exchanged')
    ]
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name="payment",null=True, blank=True)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS,null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="pending")
    metadata = models.JSONField(null=True, blank=True)  
    remarks=models.TextField(null=True,blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True) 

    def save(self, *args, **kwargs):
        if self.sale:
            self.vat_amount = self.sale.vat_amount
        super().save(*args, **kwargs)

    @property
    def total_paid(self):
        return self.amount - self.sale.refunds.aggregate(total=models.Sum("refund_amount"))["total"] or 0


    def __str__(self):
        return f"{self.sale} - {self.method} - {self.status}"




class Refund(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="refunds")
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)




class RefundItem(models.Model):
    refund = models.ForeignKey(Refund, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def total(self):
        return (self.sale_item.unit_price * self.quantity) + self.vat_amount




class Exchange(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="exchanges")
    old_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name="exchanged_from")
    new_batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    old_price = models.DecimalField(max_digits=12, decimal_places=2)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

