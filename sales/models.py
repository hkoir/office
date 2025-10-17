from django.db import models
import uuid
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from django.apps import apps
from django.db.models import Sum
from customer.models import Customer
from product.models import Product
from django.db.models import Q
from accounts.models import CustomUser
from django.utils import timezone

class CustomerQuotation(models.Model):
    customer = models.ForeignKey("customer.Customer", on_delete=models.CASCADE)
    quotation_number = models.CharField(max_length=30, unique=True, blank=True)
    date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            count = CustomerQuotation.objects.count() + 1
            self.quotation_number = f"CQ-{timezone.now().strftime('%Y%m%d')}-{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quotation_number} - {self.customer}"


class CustomerQuotationItem(models.Model):
    quotation = models.ForeignKey(CustomerQuotation, related_name="sales_quotation_items", on_delete=models.CASCADE)
    product = models.ForeignKey("product.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vat_status = models.DecimalField(max_digits=5, decimal_places=2,choices={'inclusive':'inclusive','exclusive':'inclusive'},null=True,blank=True)
    ait_status = models.DecimalField(max_digits=5, decimal_places=2,choices={'inclusive':'inclusive','exclusive':'inclusive'},null=True,blank=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)



class SaleRequestOrder(models.Model):    
    customer_quotation=models.ForeignKey(CustomerQuotation,related_name='customer_sales_quotation',on_delete=models.CASCADE,null=True, blank=True)
    order_id = models.CharField(max_length=50)
    department = models.CharField(max_length=50,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    order_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_DISPATCH', 'Ready for Dispatch'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING',null=True,blank=True)  
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    customer = models.ForeignKey(Customer, related_name='request_customer_sale', on_delete=models.CASCADE,null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks=models.TextField(null=True,blank=True)

    approval_data = models.JSONField(default=dict,null=True,blank=True)
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)

    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]

    @property
    def is_fully_ordered(self):
        for request_item in self.sale_request_order.all():
            total_ordered_quantity = SaleOrderItem.objects.filter(
                sale_request_item=request_item
            ).aggregate(total=Sum('quantity'))['total'] or 0

            if total_ordered_quantity >= request_item.quantity:
                return True
        return False
    
        
      
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"PROID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


    def __str__(self):
        return self.order_id


from purchase.models import Batch

class SaleRequestItem(models.Model):
    request_id = models.CharField(max_length=20,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    sale_request_order=models.ForeignKey(SaleRequestOrder,related_name='sale_request_order',on_delete=models.CASCADE,null=True, blank=True)
    product = models.ForeignKey(Product,related_name='sale_request_item', on_delete=models.CASCADE,null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)   
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_sale_request_item',null=True, blank=True)
    unit_selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    priority = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],null=True, blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('INSPECTED', 'INSPECTED'),
        ('DELIVERED', 'DELIVERED'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = f"SRID-{uuid.uuid4().hex[:8].upper()}"
     
        super().save(*args, **kwargs)

    def __str__(self):
        return f" ID:{self.request_id}:product: {self.product.name} qty={self.quantity}"



class SaleOrder(models.Model):
    warehouse = models.ForeignKey('inventory.warehouse',on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey('inventory.location',on_delete=models.CASCADE,null=True, blank=True)
    sale_request_order=models.ForeignKey(SaleRequestOrder,on_delete=models.CASCADE,related_name='sale_request',null=True,blank=True)
    order_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    customer = models.ForeignKey(Customer, related_name='customer_sale', on_delete=models.CASCADE,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_DISPATCH', 'Ready for Dispatch'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='IN_PROCESS',null=True,blank=True)  
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)
    remarks=models.TextField(null=True,blank=True)

    approval_data = models.JSONField(default=dict,null=True,blank=True)

    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
    # order_id incorporated in view function
    # def save(self, *args, **kwargs):
    #     if not self.order_id:
    #         self.order_id = f"OID-{uuid.uuid4().hex[:8].upper()}"
     
    #     super().save(*args, **kwargs)

    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]

    def get_warehouse(self):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None

    def get_location(self):
        Location = apps.get_model('inventory', 'Location')
        return Location.objects.get(id=self.location.id) if self.location else None


    @property
    def is_fully_delivered(self):  
        total_delivered = self.sale_shipment.all().aggregate(
        total_dispatched=Sum(
            'sale_shipment_dispatch__dispatch_quantity', 
            filter=Q(sale_shipment_dispatch__status__in=['DELIVERED','REACHED'])))['total_dispatched'] or 0
        
        total_ordered = self.sale_order.all().aggregate(
            total_ordered=Sum('quantity')
        )['total_ordered'] or 0
        return total_delivered >= total_ordered

    def __str__(self):
        return self.order_id


from decimal import Decimal
from django.db.models import F, Sum

class SaleOrderItem(models.Model):
    warehouse = models.ForeignKey('inventory.warehouse',on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey('inventory.location',on_delete=models.CASCADE,null=True, blank=True)
    sale_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    sale_order = models.ForeignKey(SaleOrder, related_name='sale_order', on_delete=models.CASCADE)
    sale_request_item = models.ForeignKey(SaleRequestItem, related_name='sale_request_item', on_delete=models.CASCADE,null=True,blank=True)
    unit_selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_sale_order_item',null=True, blank=True)
    product = models.ForeignKey(Product, related_name='product_item', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(null=True, blank=True)   
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('INSPECTED', 'INSPECTED'),
        ('DELIVERED', 'DELIVERED'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    sale_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)


    def get_warehouse(self):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None

    def get_location(self):
        Location = apps.get_model('inventory', 'Location')
        return Location.objects.get(id=self.location.id) if self.location else None

    def save(self, *args, **kwargs):
        if not self.sale_id:
            self.sale_id = f"SID-{uuid.uuid4().hex[:8].upper()}"
        if self.batch:
            self.total_price = self.quantity * self.batch.sale_price
        else:
            self.total_price = 0.0
        super().save(*args, **kwargs)

    def calculate_profit(self):
        if self.batch and self.quantity:
            purchase_price = self.batch.unit_price  # Cost price per unit
            selling_price_per_unit = self.total_price / self.quantity  # Selling price per unit
            profit_per_unit = selling_price_per_unit - purchase_price
            total_profit = profit_per_unit * self.quantity
            return round(total_profit, 2)
        return Decimal(0)
    
    @staticmethod
    def total_profit_over_time():      
        total_profit = SaleOrderItem.objects.aggregate(
            total_profit=Sum(
                (F('total_price') - (F('batch__purchase_price') * F('quantity')))
            )
        )['total_profit'] or Decimal(0)
        
        return round(total_profit, 2)

    def __str__(self):
        return f"{self.product.name}:qty:{self.quantity};"





class SaleQualityControl(models.Model):
    qc_id = models.CharField(max_length=20, null=True, blank=True)
    sale_dispatch_item = models.ForeignKey(
        'logistics.SaleDispatchItem',
        on_delete=models.CASCADE,
        related_name='sale_quality_control'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sale_quality_control_user'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='sale_qc_product',
        null=True,
        blank=True
    )
    quality_check_by = models.CharField(max_length=30,choices=[('BY-CUSTOMER','By Customer'),('BY-EMPLOYEE','By Employee')],null=True,blank=True)
    total_quantity = models.PositiveIntegerField(null=True, blank=True)
    good_quantity = models.PositiveIntegerField(null=True, blank=True)
    bad_quantity = models.PositiveIntegerField(null=True, blank=True)
    good_quantity_by_customer = models.PositiveIntegerField(null=True, blank=True)
    bad_quantity_by_customer = models.PositiveIntegerField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    inspection_date_by_customer = models.DateField(null=True, blank=True)
    status= models.CharField(max_length=15,choices=[('pending','pending'),('done','done')],null=True,blank=True)
    comments = models.TextField(null=True, blank=True)
    comments_by_customer = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
  


    def get_sale_dispatch_item(self):
        SaleDispatchItem = apps.get_model('logistics', 'SaleDispatchItem')
        return SaleDispatchItem.objects.get(id=self.sale_dispatch_item.id) if self.sale_dispatch_item else None


    def save(self, *args, **kwargs):
        self.total_quantity = self.sale_dispatch_item.dispatch_quantity
        if not self.product:
            self.product = self.sale_dispatch_item.dispatch_item.product

        if not self.qc_id:
            self.qc_id = f"QCID-{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        product_name = self.product.name if self.product else "No Product"
        return (
            f"QC-Item:{self.sale_dispatch_item}; {product_name}, "
            f"total qty= {self.total_quantity} good qty={self.good_quantity}, "
            f"bad qty={self.bad_quantity}"
        )
