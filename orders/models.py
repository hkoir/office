from decimal import Decimal
from django.conf import settings
from django.db import models

from product.models import Product
from purchase.models import Batch
from datetime import datetime
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



class Order(models.Model):
    vat_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_user')
    full_name = models.CharField(max_length=50)
    address1 = models.CharField(max_length=250)
    address2 = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    order_key = models.CharField(max_length=200)
    billing_status = models.BooleanField(default=False)
    delivery_option = models.FloatField(default=0.0)
    delivery_charge = models.FloatField(default=0.0)
  
    invoice_pdf = models.FileField(upload_to='invoices/', null=True, blank=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('paid', 'Paid'),
        ('DELIVERED', 'Delivered'),
    ]
    status = models.CharField(max_length=100,choices=STATUS_CHOICES,default='pending')
    PAYMENT_METHOD = [
        ('COD', 'COD'),
        ('online-payment', 'Online Paayment'),
       
    ]
    payment_method=models.CharField(max_length=30,choices=PAYMENT_METHOD,null=True,blank=True)
   
   
   

    class Meta:
        ordering = ('-created',)
    
    def __str__(self):
        return str(f"order by-{self.user.username} -{self.city}--phone-{self.phone}--Order ID:-{self.order_key}")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, related_name='order_batch', on_delete=models.CASCADE,null=True,blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1) 
    vat_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    product_code = models.CharField(
        verbose_name=_("Product Code"),
        max_length=20,
        unique=True,
        help_text=_("Unique product code identifier"),
        null=True,
        blank=True,
    )
    created = models.DateTimeField(default=timezone.now)

    DELIVER_STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
         ('ON_THE_WAY', 'on the way'),
        ('DELIVERED', 'Delivered'),
    ]

    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVER_STATUS_CHOICES,
        default='IN_PROCESS',
    )

    CONFIRMATION_STATUS_CHOICES = [
        ('NOT_CONFIRMED', 'not confirmed'),
         ('CONFIRMED', 'confirmed'),
       
    ]

    confirmation_status = models.CharField(
        max_length=20,
        choices=CONFIRMATION_STATUS_CHOICES,
        default='NOT_CONFIRMED',
    )


    def __str__(self):
        return str(self.product)