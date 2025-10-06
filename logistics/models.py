
from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
import uuid
from django.core.exceptions import ValidationError
from django.db.models import Sum,F,ExpressionWrapper,DecimalField

from inventory.models import Warehouse,Location
from sales.models import SaleOrderItem,SaleOrder
from purchase.models import PurchaseOrder,PurchaseOrderItem
from accounts.models import CustomUser
from django.utils import timezone

#######################################################################################################


class PurchaseShipment(models.Model):
    shipment_id = models.CharField(max_length=50,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_shipment_user')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE,
        related_name='purchase_shipment')
    carrier = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=50, unique=True)
    estimated_delivery = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2,null=True,blank=True)
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
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='PENDING')   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    @property
    def total_amount(self):
        shipment_items = self.shipment_dispatch_item.all()        
        total = shipment_items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('dispatch_quantity') * F('dispatch_item__batch__purchase_price'),  
                    output_field=DecimalField()
                )
            )
        )['total'] or 0
        return total


    @property
    def is_fully_shipped(self):
        total_shipped = self.shipment_dispatch_item.all().aggregate(
            total_shipped=Sum('dispatch_quantity')
        )['total_shipped'] or 0  

        total_ordered = self.purchase_order.purchase_order_item.all().aggregate(
            total_ordered=Sum('quantity')
        )['total_ordered'] or 0  

        return total_shipped >= total_ordered    
    @property
    def is_fully_invoiced(self):
        total_invoiced = self.shipment_invoices.aggregate(total_invoiced=Sum('amount_due'))['total_invoiced'] or 0        
        return total_invoiced >= self.total_amount

    def update_shipment_status(self):       
        dispatch_items = self.shipment_dispatch_item.all() 
        all_received = dispatch_items.filter(status__in=['RECEIVED','OBI','DELIVERED']).count() == dispatch_items.count()
        any_in_process = dispatch_items.filter(status='IN_PROCESS').exists()
        any_in_custom = dispatch_items.filter(status='CUSTOM_CLEARANCE_IN_PROCESS').exists()
        any_in_transit = dispatch_items.filter(status__in=['IN_TRANSIT', 'ON_BOARD']).exists()
        
        if all_received:
            self.status = 'DELIVERED'
        elif any_in_process:
            self.status = 'IN_PROCESS'
        elif any_in_transit:
            self.status = 'IN_TRANSIT'
        elif any_in_custom:
            self.status = 'CUSTOM_CLEARANCE_IN_PROCESS'
        else:
            self.status = 'PENDING'

        self.save()       
    def save(self, *args, **kwargs):
        if not self.shipment_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.shipment_id = f"SID-{timestamp}-{unique_id}"
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f" {self.shipment_id}-{self.total_amount}"
  


class PurchaseDispatchItem(models.Model):
    dispatch_id=models.CharField(max_length=20,null=True,blank=True)
    purchase_shipment = models.ForeignKey(PurchaseShipment,on_delete=models.CASCADE,
        related_name='shipment_dispatch_item',null=True, blank=True
    )
    dispatch_item = models.ForeignKey(PurchaseOrderItem,on_delete=models.CASCADE,
        related_name='order_dispatch_item',null=True, blank=True
    )    
    dispatch_quantity = models.PositiveIntegerField(null=True, blank=True)
    dispatch_date = models.DateField(null=True, blank=True) 
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=100,  null=True, blank=True, default='IN_PROCESS',   
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
    )  
    user = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):

        if self.dispatch_item and self.dispatch_quantity:
            available_quantity = self.dispatch_item.quantity
            if self.dispatch_quantity > available_quantity:
                raise ValidationError(
                    f"Dispatch quantity ({self.dispatch_quantity}) cannot exceed available quantity ({available_quantity}) of the purchase order item."
                )

    def save(self, *args, **kwargs):
        if not self.dispatch_id:
            self.dispatch_id = f"DIID-{uuid.uuid4().hex[:8].upper()}"
        self.clean()
        super().save(*args, **kwargs)             
     
    def __str__(self):
        return f"{self.dispatch_quantity} of {self.dispatch_item.product.name} dispatched"



############# sale section #################################################################


class SaleShipment(models.Model):
    shipment_id = models.CharField(max_length=50,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='sale_shipment_user')
    sales_order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE,related_name='sale_shipment')
    carrier = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=50, unique=True)
    estimated_delivery = models.DateField()
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
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
  
    
    @property
    def total_amount(self):
        shipment_items = self.sale_shipment_dispatch.all()        
        total = shipment_items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('dispatch_quantity') * F('dispatch_item__product__unit_price'),  
                    output_field=DecimalField()
                )
            )
        )['total'] or 0
        return total
    
    @property
    def is_fully_invoiced(self):
        total_invoiced = self.sale_shipment_invoices.aggregate(total_invoiced=Sum('amount_due'))['total_invoiced'] or 0        
        return total_invoiced >= self.total_amount

    @property
    def is_fully_shipped(self):
        total_shipped = self.sale_shipment_dispatch.all().aggregate(
            total_shipped=Sum('dispatch_quantity')
        )['total_shipped'] or 0  

        total_ordered = self.sales_order.sale_order.all().aggregate(
            total_ordered=Sum('quantity')
        )['total_ordered'] or 0  
        return total_shipped >= total_ordered
        
        
    def update_shipment_status(self):    
        dispatch_items = self.sale_shipment_dispatch.all() 
        all_received = dispatch_items.filter(status__in=['RECEIVED','OBI','DELIVERED']).count() == dispatch_items.count()
        any_in_process = dispatch_items.filter(status='IN_PROCESS').exists()
        any_in_custom = dispatch_items.filter(status='CUSTOM_CLEARANCE_IN_PROCESS').exists()
        any_in_transit = dispatch_items.filter(status__in=['IN_TRANSIT', 'ON_BOARD']).exists()
        
        if all_received:
            self.status = 'DELIVERED'
        elif any_in_process:
            self.status = 'IN_PROCESS'
        elif any_in_transit:
            self.status = 'IN_TRANSIT'
        elif any_in_custom:
            self.status = 'CUSTOM_CLEARANCE_IN_PROCESS'
        else:
            self.status = 'PENDING'

        self.save()

    def save(self, *args, **kwargs):
        if not self.shipment_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_id = str(uuid.uuid4().hex)[:6]  
            self.shipment_id = f"SSID-{timestamp}-{unique_id}"
        if not self.tracking_number:
            self.tracking_number = f"TRAC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return F"{self.shipment_id}-{self.total_amount}"
  
      
  

from purchase.models import Batch

class SaleDispatchItem(models.Model):
    dispatch_id=models.CharField(max_length=20,null=True,blank=True)
    sale_shipment = models.ForeignKey(SaleShipment,on_delete=models.CASCADE,
        related_name='sale_shipment_dispatch',null=True, blank=True
    )
    dispatch_item = models.ForeignKey(SaleOrderItem,on_delete=models.CASCADE,
        related_name='sale_dispatch_item',null=True, blank=True)    

    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_sale_dispatch',null=True, blank=True)  
    unit_selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dispatch_quantity = models.PositiveIntegerField(null=True, blank=True)

    warehouse = models.ForeignKey(Warehouse,on_delete=models.CASCADE,related_name='dispatch_warehouse',null=True,blank=True)
    location = models.ForeignKey(Location,on_delete=models.CASCADE,related_name='dispatch_location',null=True,blank=True)
    dispatch_date = models.DateField(null=True, blank=True) 
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=100,  null=True, blank=True, default='IN_PROCESS',   
    choices=[
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
    ],
    )  
    user = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):

        if self.dispatch_item and self.dispatch_quantity:
            available_quantity = self.dispatch_item.quantity
            if self.dispatch_quantity > available_quantity:
                raise ValidationError(
                    f"Dispatch quantity ({self.dispatch_quantity}) cannot exceed available quantity ({available_quantity}) of the purchase order item."
                )

    def save(self, *args, **kwargs):
        if not self.dispatch_id:
            self.dispatch_id = f"SDIID-{uuid.uuid4().hex[:8].upper()}"
        if not self.unit_selling_price:
            self.unit_selling_price = self.dispatch_item.sale_request_item.unit_selling_price if self.dispatch_item.sale_request_item.unit_selling_price else 0
        self.clean()
        super().save(*args, **kwargs)     
         
     

    def __str__(self):
        return f"{self.dispatch_quantity} of {self.dispatch_item.product.name} dispatched"
