from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
import uuid
from django.apps import apps
from django.core.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)

from supplier.models import Supplier
from product.models import Product,Component
from django.apps import apps
from accounts.models import CustomUser



class PurchaseRequestOrder(models.Model):
    order_id = models.CharField(max_length=50,null=True,blank=True)
    department = models.CharField(max_length=50,null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_request_user')
    order_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 

    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='requester_orders')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewer_orders')
    approver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approver_orders')
    
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)
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

    
    def save(self, *args, **kwargs):
        if not self.requester:
            self.requester = CustomUser.objects.filter(groups__name='Requester').first()
        if not self.reviewer:
            self.reviewer = CustomUser.objects.filter(groups__name='Reviewer').first()
        if not self.approver:
            self.approver = CustomUser.objects.filter(groups__name='Approver').first()

        if not self.order_id:
            self.order_id= f"PRID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)



    @property
    def is_fully_delivered(self):  
        total_delivered = self.purchase_order_request_order.all().aggregate(
            total_dispatched=Sum('purchase_order_item__order_dispatch_item__dispatch_quantity')  # Adjust related names
        )['total_dispatched'] or 0

        total_ordered = self.purchase_request_order.all().aggregate(
            total_ordered=Sum('quantity')  
        )['total_ordered'] or 0

        return total_delivered >= total_ordered

    def __str__(self):
        product_details = ", ".join(
            f"{item.product.name} (Qty: {item.quantity})"
            for item in self.purchase_request_order.all()
        )
        return self.order_id
       

class PurchaseRequestItem(models.Model):
    item_request_id = models.CharField(max_length=20,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_request_item_user')
    purchase_request_order=models.ForeignKey(PurchaseRequestOrder,related_name='purchase_request_order',on_delete=models.CASCADE)
    product = models.ForeignKey(Product,related_name='purchase_request_item', on_delete=models.CASCADE)   
    quantity = models.PositiveIntegerField() 
    priority = models.CharField(max_length=20, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')])
    total_price = models.DecimalField(max_digits=15,decimal_places=2, null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self,*args,**kwargs):
        if not self.item_request_id:
            self.item_request_id= f"RIID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args,*kwargs)

    def __str__(self):
        return f" {self.item_request_id}:{self.product.name}:{self.quantity}nos"


from django.db.models import Q
import uuid
from django.utils.timezone import now


class Batch(models.Model):
    NEW_PURCHASE = 'NEW'
    EXISTING_PRODUCT = 'EXISTING'
    
    PRODUCT_TYPE_CHOICES = [
        (NEW_PURCHASE, 'New Purchase'),
        (EXISTING_PRODUCT, 'Existing Product'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='batch_user')
    batch_number = models.CharField(max_length=50, unique=True, editable=False)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default=NEW_PURCHASE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)   
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=20, decimal_places=2)
    sale_price = models.DecimalField(max_digits=20, decimal_places=2,null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs): 
        if not self.batch_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.batch_number = f"BATCH-{timestamp}-{unique_id}"

        if not self.id:
            self.remaining_quantity = self.quantity

        if self.sale_price is None or self.sale_price == 0:
            self.sale_price = self.unit_price


        super().save(*args, **kwargs)

    def __str__(self):
        inventory = self.batch_inventory.first()  
        warehouse_name = inventory.warehouse.name if inventory else "No Warehouse"  
        return f'Batch - Product Type: {self.get_product_type_display()} - {self.product} - Unit Price={self.unit_price} - Available: {self.remaining_quantity} - Warehouse: {warehouse_name}'



class PurchaseOrder(models.Model):
    order_id = models.CharField(max_length=20)
    purchase_request_order = models.ForeignKey(PurchaseRequestOrder, 
        on_delete=models.CASCADE, null=True, blank=True,related_name='purchase_order_request_order')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_order_user')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_supplier')
    order_date = models.DateField(null=True, blank=True)
    ORDER_STATUS_CHOICES = [
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
        ]
    status = models.CharField(max_length=50, choices=ORDER_STATUS_CHOICES, default='IN_PROCESS',null=True,blank=True)   
    APPROVAL_STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),
     ('REVIEWED', 'Reviewed'),
    ('APPROVED', 'Approved'),   
    ('CANCELLED','Cancelled'),
        ]
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='SUBMITTED',null=True, blank=True) 
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True)

    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_requester')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_reviewer')
    approver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_approvar')
    
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

    def save(self, *args, **kwargs):
        if not self.requester:
            self.requester = CustomUser.objects.filter(groups__name='Requester').first()
        if not self.reviewer:
            self.reviewer = CustomUser.objects.filter(groups__name='Reviewer').first()
        if not self.approver:
            self.approver = CustomUser.objects.filter(groups__name='Approver').first()

        if not self.order_id:
            self.order_id= f"PROID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

        
    def __str__(self):
        return self.order_id
    
    @property
    def is_fully_delivered(self):
        total_delivered_agg = self.purchase_shipment.all().aggregate(
            total_dispatched=Sum('shipment_dispatch_item__dispatch_quantity', filter=Q(shipment_dispatch_item__status='DELIVERED'))
        )
        total_delivered = total_delivered_agg['total_dispatched'] if total_delivered_agg and total_delivered_agg['total_dispatched'] is not None else 0
       
        total_ordered_agg = self.purchase_order_item.all().aggregate(
            total_ordered=Sum('quantity')
        )
        total_ordered = total_ordered_agg['total_ordered'] if total_ordered_agg and total_ordered_agg['total_ordered'] is not None else 0
       
        return total_delivered >= total_ordered
    


class PurchaseOrderItem(models.Model):
    order_item_id = models.ForeignKey(PurchaseRequestItem,on_delete=models.CASCADE,related_name='order_request_item',null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_order_item_user')
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='purchase_order_item', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_purchase_order_item',null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchases', null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)  # Total quantity ordered
    total_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prepared_by = models.ForeignKey(CustomUser, related_name='prepared_purchases', on_delete=models.CASCADE, null=True, blank=True)
    approved_by = models.ForeignKey(CustomUser, related_name='approved_purchases', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(
    max_length=50,
    choices=[
        ('IN_PROCESS', 'In Process'),
        ('READY_FOR_QC', 'Ready for QC'),
        ('DISPATCHED', 'Dispatched'),
        ('ON_BOARD', 'On Board'),
        ('IN_TRANSIT', 'In Transit'),
        ('CUSTOM_CLEARANCE_IN_PROCESS', 'Custom Clearance In Process'),   
        ('REACHED', 'Reached'),         
        ('OBI','OBI done'),
        ('DELIVERED', 'Delivered'),     
        ('CANCELLED', 'Cancelled'),
    ],
    null=True,
    blank=True,
    default='IN_PROCESS'
)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)


  

    @property
    def quantity_dispatch(self):
        related_items = self.related_item_dispatch.all()  # Get all related dispatch items
        logger.info(f"Related dispatch items: {related_items}")
        total_dispatch = self.related_item_dispatch.aggregate(total_dispatched=Sum('dispatch_quantity'))['total_dispatched'] or 0
        return total_dispatch

    @property
    def remaining_to_dispatch(self):
        return (self.quantity or 0) - self.quantity_dispatch

    def __str__(self):
        return f"{self.quantity} nos {self.product.name}"
    
    
    def save(self,*args,**kwargs):      
        if not self.total_price:
             self.total_price = self.quantity * self.batch.unit_price
        super().save(*args,**kwargs)
    

#


class QualityControl(models.Model):
    purchase_dispatch_item = models.ForeignKey('logistics.PurchaseDispatchItem', on_delete=models.CASCADE,
         related_name='quality_control',null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='quality_control_user')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='qc_product', null=True, blank=True)
    total_quantity = models.PositiveIntegerField(null=True, blank=True)
    good_quantity = models.PositiveIntegerField(null=True, blank=True)
    bad_quantity = models.PositiveIntegerField(null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

  

    def save(self):
        PurchaseDispatchItem = apps.get_model('logistics', 'PurchaseDispatchItem')
        return PurchaseDispatchItem.objects.get(id=self.purchase_dispatch_item.id) if self.purchase_dispatch_item else None
     

    def save(self,*args,**kwargs):
        self.total_quantity = self.purchase_dispatch_item.dispatch_quantity
        if not self.product:
             self.product = self.purchase_dispatch_item.dispatch_item.product

        super().save(*args,**kwargs)

    def __str__(self):
        return f" QC{self.product.name},total qty: {self.total_quantity} good qty={self.good_quantity}, bad qty={self.bad_quantity}"




class ReceiveGoods(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='received_goods')
    quality_control = models.ForeignKey(QualityControl, on_delete=models.CASCADE, related_name='qc_goods')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  
    warehouse = models.ForeignKey('inventory.warehouse', on_delete=models.CASCADE, related_name='received_goods_warehouse',null=True, blank=True)
    location = models.ForeignKey('inventory.location', on_delete=models.CASCADE, null=True, blank=True,related_name='received_goods_location')
    quantity_received = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='received_goods')

    RECEIVE_STATUS_CHOICES = [
        ('RECEIVED', 'RECEIVED'),
        ('PENDING', 'PENDING'),
    ]
    receive_status = models.CharField(max_length=20, null=True, blank=True, choices=RECEIVE_STATUS_CHOICES, default='PENDING')
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

    def save(self,*args,**kwargs):
       self.product = self.quality_control.product.name
       self.quantity_received = self.quality_control.good_quantity
       super().save(*args,**kwargs)

    def __str__(self):
        return f"{self.quantity_received} of {self.product.name} received at {self.warehouse.name}"
