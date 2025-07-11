from django.db import models
import uuid
import logging
logger = logging.getLogger(__name__)
from simple_history.models import HistoricalRecords
from accounts.models import User
from product.models import Product,Category
from django.apps import apps
from django.contrib.auth.decorators import permission_required
from django.utils import timezone
from accounts.models import CustomUser
from purchase.models import Batch

class ExistingOrder(models.Model):
    order_id = models.CharField(max_length=20)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='operations_order_user')
    order_date = models.DateField(null=True, blank=True)
    ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ADDED', 'Added into stock'),
    ('CANCELLED', 'Cancelled'),
        ]
    
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING',null=True,blank=True)   
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)   
    remarks=models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]
    def save(self, *args, **kwargs):     
        if not self.order_id:
            self.order_id= f"OEOID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)        
    def __str__(self):
        return f" purchase_order:{self.order_id}"

  



class ExistingOrderItems(models.Model):
    item_id = models.CharField(max_length=20)
    existing_order = models.ForeignKey(ExistingOrder, 
        on_delete=models.CASCADE, null=True, blank=True,related_name='operations_existing_order_items')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='operations_order_items_user')
    product = models.ForeignKey(Product,related_name='operations_order_product', on_delete=models.CASCADE) 
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_existing_item')
    order_date = models.DateField(null=True, blank=True)
    ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ADDED', 'Added into stock'),
    ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING',null=True,blank=True)   
    quantity = models.PositiveIntegerField() 
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    remarks=models.TextField(null=True,blank=True)   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def save(self, *args, **kwargs):
        if not self.item_id:
            self.item_id= f"OEIID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)   

    def __str__(self):
        return f'{self.item_id} for {self.product}'

    
    

class OperationsRequestOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)   
    order_id = models.CharField(max_length=50,null=True,blank=True)
    department = models.CharField(max_length=50,null=True, blank=True)
   
    order_date = models.DateField(null=True, blank=True)
    ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 

    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
       
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
   
    remarks=models.TextField(null=True,blank=True)   
   
    approval_data = models.JSONField(default=dict,null=True,blank=True)
   
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)   
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)
   
    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]
  
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id= f"OPROID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.order_id}'


class OperationsRequestItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    item_id = models.CharField(max_length=20, unique=True)   
    operations_request_order = models.ForeignKey(OperationsRequestOrder, related_name='operations_request_items', on_delete=models.CASCADE, null=True, blank=True)
    purpose = models.CharField(max_length=150)
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='operations_product_request',null=True,blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_operation_request_item')
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    priority = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')])
    
    STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   

    def save(self, *args, **kwargs):
        if not self.item_id:
            self.item_id= f"ORID-{uuid.uuid4().hex[:8].upper()}"
        self.total_amount = self.quantity * self.product.unit_price
        super().save(*args, **kwargs)   

    def __str__(self):
        return f' { self.item_id}:{self.product}-{self.quantity} nos'



class OperationsDeliveryItem(models.Model):
    operations_request_order = models.ForeignKey(OperationsRequestOrder, related_name='operations_request_order_delivery', on_delete=models.CASCADE,null=True, blank=True)
    operations_request_item = models.ForeignKey(OperationsRequestItem, related_name='operations_request_items_delivery', on_delete=models.CASCADE,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    item_id = models.CharField(max_length=20)
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True)
   
    item_type = models.CharField(max_length=10, choices=[('PRODUCT', 'Product'), ('COMPONENT', 'Component')])
    product = models.ForeignKey(Product, related_name='operations_product_item_delivery', on_delete=models.CASCADE, null=True, blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_operation_delivery_item')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    STATUS_CHOICES = [ 
    ('DELIVERED', 'Delivered'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 

    def get_warehouse(self):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None

    def get_location(self):
        Location = apps.get_model('inventory', 'Location')
        return Location.objects.get(id=self.location.id) if self.location else None    

    def save(self, *args, **kwargs):
        if not self.item_id:
            self.item_id= f"ODIID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_id} for {self.product}" 