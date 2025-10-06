from django.db import models
from django.utils import timezone
from clients.models import Client



class PaymentSystem(models.Model):
    PAYMENT_METHODS = (
        ('bKash', 'bKash'),
        ('Rocket', 'Rocket'),
        ('CreditCard', 'CreditCard'),
        ('PayPal', 'PayPal'),
        ('sslcommerz', 'SSLCOMERZ'),
        ('aamarPay', 'Aamar Pay'),
        ('surujPay', 'Suruj Pay'),
        ('others', 'Others'),
        
    )    
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    name = models.CharField(max_length=255)  
    base_url = models.URLField(blank=True, null=True)
  

    def __str__(self):
        return self.name
    


class TenantPaymentConfig(models.Model):
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE)
    payment_system = models.ForeignKey(PaymentSystem, on_delete=models.CASCADE,null=True,blank=True)    
    api_key = models.CharField(max_length=255, blank=True, null=True) 
    merchant_id = models.CharField(max_length=255, blank=True, null=True)
    payment_redirect_url = models.URLField(blank=True, null=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)  
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    enable_payment_gateway = models.BooleanField(default=True)
    ait = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)


    def __str__(self):
        return f"Payment config for {self.tenant.name}"




from datetime import time
from django.utils.timezone import now
from orders.models import Order
from customer.models import Customer

class PaymentInvoice(models.Model):
    INVOICE_TYPES = [      
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('online_sales', 'Online Sales'),
        ('Others', 'Others'),
    
    ]

    customer = models.ForeignKey(Customer,on_delete=models.CASCADE,null=True,blank=True,related_name='customer_invoices')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True,related_name='order_payments')
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    invoice_type = models.CharField(max_length=30, choices=INVOICE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    tran_id = models.CharField(max_length=100, unique=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice_type} — ৳{self.amount}"


    def save(self, *args, **kwargs):
        if not self.tran_id:            
            self.tran_id = f"txn_{now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)



class Payment(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    invoice = models.ForeignKey(PaymentInvoice, on_delete=models.CASCADE, related_name='payment_invoices')  # NEW
    customer = models.ForeignKey(Customer,on_delete=models.CASCADE,null=True,blank=True,related_name='customer_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)  # VALID, FAILED, CANCELLED
    method = models.CharField(max_length=100, blank=True, null=True)  # bKash, Visa, Rocket
    gateway_response = models.TextField(blank=True, null=True)  
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} ({self.status})"
