from django.db import models
from django.contrib.auth.models import User 
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
import uuid
from accounts.models import CustomUser

from logistics.models import PurchaseShipment,SaleShipment
from django.db.models import Sum
from decimal import Decimal



class PurchaseInvoice(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_invoice_user')
    purchase_shipment = models.ForeignKey(PurchaseShipment, related_name='shipment_invoices', on_delete=models.CASCADE, null=True, blank=True)
    invoice_number = models.CharField(max_length=150, unique=True, blank=True, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, null=True, blank=True,
        choices=[
            ('SUBMITTED', 'Submitted'),
            ('FULLY_PAID', 'Fully Paid'),
            ('PARTIALLY_PAID', 'Partially Paid'),
            ('CANCELLED', 'Cancelled')
        ]
    )
    
    AIT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    AIT_type = models.CharField(max_length=50, choices=[('inclusive', 'inclusive'), ('exclusive', 'exclusive')], null=True, blank=True)
    VAT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    VAT_type = models.CharField(max_length=50, choices=[('inclusive', 'inclusive'), ('exclusive', 'exclusive')], null=True, blank=True)
    issued_date = models.DateTimeField(null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    ait_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_due_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Added for calculation
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_tax_amounts(self):
        base_amount = Decimal(self.amount_due or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat_rate = Decimal(self.VAT_rate or 0) / 100
        ait_rate = Decimal(self.AIT_rate or 0) / 100

        if self.AIT_type == 'inclusive':
            self.ait_amount = (base_amount - (base_amount / (1 + ait_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_amount -= self.ait_amount  # Adjust base for VAT calculation
        else:
            self.ait_amount = (base_amount * ait_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  

        if self.VAT_type == 'inclusive':
            self.vat_amount = (base_amount - (base_amount / (1 + vat_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_amount -= self.vat_amount  # Adjust base after VAT extraction
        else:
            self.vat_amount = (base_amount * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if self.VAT_type == 'exclusive':
            base_amount += self.vat_amount
        if self.AIT_type == 'exclusive':
            base_amount += self.ait_amount

        self.net_due_amount = base_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


   
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"PINV-{uuid.uuid4().hex[:8].upper()}"
        self.calculate_tax_amounts()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - VAT: {self.vat_amount} - AIT: {self.ait_amount} - Net Due: {self.net_due_amount}"
    
    @property
    def total_paid_amount(self):
        return self.purchase_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or 0

    @property
    def is_fully_paid(self):
        total_paid = self.purchase_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or 0
        return total_paid >= self.net_due_amount
    @property
    def remaining_balance(self):
        total_paid = self.purchase_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or 0
        return self.net_due_amount - total_paid



class PurchaseInvoiceAttachment(models.Model):
    purchase_invoice = models.ForeignKey(PurchaseInvoice, related_name='purchase_invoice_attachment', on_delete=models.CASCADE)
    file = models.ImageField(upload_to='purchase_invoice/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PurchasePayment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_payment_user')
    purchase_invoice = models.ForeignKey(PurchaseInvoice, related_name='purchase_payment_invoice', on_delete=models.CASCADE, null=True, blank=True) 
    payment_id =models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'), 
        ('CREDIT', 'Credit Card'), 
        ('BANK', 'Bank Transfer')
    ])

    status = models.CharField(max_length=20,null=True,blank=True,
            choices=[
                ('IN_PROCESS','In Process'),
                ('FULLY_PAID','Fully Paid'),
                 ('PARTIALLY_PAID','Partially Paid')
            ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PPAYID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment of {self.amount} for Purchase Order {self.purchase_invoice.invoice_number}"
    
    # @property
    # def is_fully_paid(self):
    #     total_invoice = self.purchase_invoice.aggregate(Sum('amount_due'))['amount_due__sum'] or Decimal(0)
    #     tolerance = Decimal('0.01')  
    #     return abs(total_invoice - self.amount) <= tolerance 
        
    @property
    def is_fully_paid(self):
        total_paid = self.purchase_invoice.purchase_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        tolerance = Decimal('0.01')  # Small tolerance for floating-point calculations
        return abs(total_paid - self.purchase_invoice.amount_due) <= tolerance

class PurchasePaymentAttachment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    purchase_invoice = models.ForeignKey(PurchaseInvoice, related_name='purchase_payment_attachment', on_delete=models.CASCADE)
    file = models.ImageField(upload_to='purchase_payment/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

############ sales ##############################################################


from decimal import Decimal, ROUND_HALF_UP
class SaleInvoice(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='sale_invoice_user')
    sale_shipment = models.ForeignKey(SaleShipment, related_name='sale_shipment_invoices', on_delete=models.CASCADE,null=True,blank=True)
    invoice_number = models.CharField(max_length=150, unique=True, blank=True, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)   
    issued_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20,null=True,blank=True,
            choices=[
                ('SUBMITTED','Submitted'),
                ('FULLY_PAID','Fully Paid'),
                ('PARTIALLY_PAID','Partially Paid'),
                ('CANCELLED','Cancelled')
            ])
    AIT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    AIT_type = models.CharField(max_length=50, choices=[('inclusive', 'inclusive'), ('exclusive', 'exclusive')], null=True, blank=True)
    VAT_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    VAT_type = models.CharField(max_length=50, choices=[('inclusive', 'inclusive'), ('exclusive', 'exclusive')], null=True, blank=True)
    issued_date = models.DateTimeField(null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    ait_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_due_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Added for calculation
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def calculate_tax_amounts(self):
        base_amount = Decimal(self.amount_due or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat_rate = Decimal(self.VAT_rate or 0) / 100
        ait_rate = Decimal(self.AIT_rate or 0) / 100

        if self.AIT_type == 'inclusive':
            self.ait_amount = (base_amount - (base_amount / (1 + ait_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_amount -= self.ait_amount  # Adjust base for VAT calculation
        else:
            self.ait_amount = (base_amount * ait_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  

        if self.VAT_type == 'inclusive':
            self.vat_amount = (base_amount - (base_amount / (1 + vat_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            base_amount -= self.vat_amount  # Adjust base after VAT extraction
        else:
            self.vat_amount = (base_amount * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if self.VAT_type == 'exclusive':
            base_amount += self.vat_amount
        if self.AIT_type == 'exclusive':
            base_amount += self.ait_amount

        self.net_due_amount = base_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)




    @property
    def is_fully_paid(self):
        total_paid = self.sale_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        tolerance = Decimal('0.01')  
        return abs(total_paid - self.amount_due) <= tolerance 
    
    @property
    def remaining_balance(self):
        total_paid = self.sale_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or 0
        return self.net_due_amount - total_paid



    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"SINV-{uuid.uuid4().hex[:8].upper()}"
        self.calculate_tax_amounts()
        super().save(*args, **kwargs)

    def __str__(self):
          return f"Invoice {self.invoice_number} - VAT: {self.vat_amount} - AIT: {self.ait_amount} - Net Due: {self.net_due_amount}"


class SaleInvoiceAttachment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    sale_invoice = models.ForeignKey(SaleInvoice, related_name='sale_invoice_attachment', on_delete=models.CASCADE)
    file = models.ImageField(upload_to='sale_invoice/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SalePayment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='sale_payment_user')
    sale_invoice = models.ForeignKey(SaleInvoice, related_name='sale_payment_invoice', on_delete=models.CASCADE, null=True, blank=True) 
    payment_id =models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'), 
        ('CREDIT', 'Credit Card'), 
        ('BANK', 'Bank Transfer')
    ])

    status = models.CharField(max_length=20,null=True,blank=True,
            choices=[
                ('IN_PROCESS','IN Process'),
                 ('FULLY_PAID','Fully Paid'),
                 ('PARTIALLY_PAID','Partially Paid')
            ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
  

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"SPAYID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment of {self.amount} for Sale Order {self.sale_invoice.invoice_number}"
    

    
    @property
    def is_fully_paid(self):
        total_paid = self.sale_invoice.sale_payment_invoice.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        tolerance = Decimal('0.01')  # To account for rounding issues
        return abs(self.sale_invoice.amount_due - total_paid) <= tolerance
    
class SalePaymentAttachment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    sale_invoice = models.ForeignKey(SaleInvoice, related_name='sale_payment_attachement', on_delete=models.CASCADE)
    file = models.ImageField(upload_to='sale_payment/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)