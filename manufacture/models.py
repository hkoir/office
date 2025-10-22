
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.apps import apps

from product.models import Product,Component,BOM

from core.utils import DEPARTMENT_CHOICES
from accounts.models import CustomUser
from purchase.models import Batch

class MaterialsRequestOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)   
    order_id = models.CharField(max_length=50,null=True,blank=True)
    department = models.CharField(max_length=50,null=True, blank=True,choices=DEPARTMENT_CHOICES)
   
    order_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
    ('CREATED', 'Created'), 
     ('IN_PROCESS', 'In Process'),
    ('IN_TRANSIT', 'In Transit'),
    ('DELIVERED', 'Delivered'),
    ('PARTIAL_DELIVERED', 'Partial Delivered'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 

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

    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  
    
    class Meta:
        permissions = [
            ("can_request", "can request"),
            ("can_review", "Can review"),
            ("can_approve", "Can approve"),
        ]
  
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id= f"MRO-{uuid.uuid4().hex[:8].upper()}"

        if not self.order_date:
            self.order_date = self.created_at

        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_id or f"Order #{self.pk}" or "Unnamed Order"




class MaterialsRequestItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    item_id = models.CharField(max_length=20, unique=True)   
    material_request_order = models.ForeignKey(MaterialsRequestOrder, related_name='material_request_order_for_item', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_request',null=True,blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_manufacture',null=True,blank=True)
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    production_section = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')])
    created_at = models.DateField(auto_now_add=True)

    STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    updated_at = models.DateTimeField(auto_now=True)
 

    def save(self, *args, **kwargs):
        if not self.item_id:
            self.item_id= f"CAT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)   

    def __str__(self):
        return self.item_id



class MaterialsDeliveryItem(models.Model):
    materials_request_order = models.ForeignKey(MaterialsRequestOrder, related_name='materials_request_delivery', on_delete=models.CASCADE,null=True, blank=True)
    materials_request_item = models.ForeignKey(MaterialsRequestItem, related_name='materials_request_items', on_delete=models.CASCADE,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    item_id = models.CharField(max_length=20)
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True)
   
    item_type = models.CharField(max_length=10, choices=[('PRODUCT', 'Product'), ('COMPONENT', 'Component')])
    product = models.ForeignKey(Product, related_name='product_item_for_delivery', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_manufacture_delivery',null=True,blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
    STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
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
            self.item_id= f"CAT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_id} for product {self.product}" 
    

class FinishedGoodsReadyFromProduction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    goods_id = models.CharField(max_length=20)
    materials_request_order = models.ForeignKey(MaterialsRequestOrder, on_delete=models.CASCADE,null=True,blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_finished_goods',null=True,blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
    ('DELIVERED', 'Delivered'),
    ('RECEIVED', 'Received'),
    ('CANCELLED','Cancelled'),
        ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
 

    def save(self, *args, **kwargs):
        if not self.goods_id:
            self.goods_id = f"FGID-{uuid.uuid4().hex[:8].upper()}"  # Check this format
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} is ready {self.quantity} nos"


class ManufactureQualityControl(models.Model):
    finish_goods_from_production = models.ForeignKey(FinishedGoodsReadyFromProduction,
         on_delete=models.CASCADE,related_name='goods_quality')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)
    total_quantity = models.PositiveIntegerField(null=True, blank=True)
    good_quantity = models.PositiveIntegerField(null=True, blank=True)
    bad_quantity = models.PositiveIntegerField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

      

    def save(self,*args,**kwargs):
        self.total_quantity = self.finish_goods_from_production.quantity
        if not self.product:
             self.product = self.finish_goods_from_production.product

        super().save(*args,**kwargs)

    def __str__(self):
        return f" QC{self.product.name},total qty: {self.total_quantity} good qty={self.good_quantity}, bad qty={self.bad_quantity}"



class ReceiveFinishedGoods(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    quality_control=models.ForeignKey(ManufactureQualityControl,on_delete=models.CASCADE,related_name='quality_received')
    receiving_id = models.CharField(max_length=20)      
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE, related_name='received_finish_goods',null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
   
    RECEIVE_STATUS_CHOICES = [
        ('RECEIVED', 'RECEIVED'),
        ('PENDING', 'PENDING'),
         ('CANCELLED','Cancelled'),
    ]
    status = models.CharField(max_length=20, null=True, blank=True, default='PENDING')
    received_at = models.DateTimeField(default=timezone.now)
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
        if self.quality_control:
            self.quantity = self.quality_control.good_quantity
        super().save(*args, **kwargs)
  
    def __str__(self):
        return f"{self.quantity} of {self.quality_control} received at {self.received_at}"
















