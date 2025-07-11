
from django.db import models
import uuid
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.apps import apps
from simple_history.models import HistoricalRecords

import logging
logger = logging.getLogger(__name__)

from product.models import Product
from manufacture.models import MaterialsRequestOrder
from sales.models import SaleOrder
from manufacture.models import ReceiveFinishedGoods
from purchase.models import PurchaseOrder

from accounts.models import CustomUser


class Warehouse(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True,related_name='warehouse_user')
    name = models.CharField(max_length=100)
    warehouse_id = models.CharField(max_length=150, unique=True, null=True, blank=True)  
    address = models.CharField(max_length=255, blank=True, null=True)
    city=models.CharField(max_length=100,null=True,blank=True)
    description = models.TextField(blank=True, null=True)
    reorder_level = models.PositiveIntegerField(default=10,null=True,blank=True)
    lead_time = models.PositiveIntegerField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.warehouse_id:
            self.warehouse_id = f"WH-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f" {self.name} "



class Location(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True,related_name='location_user')
    location_id = models.CharField(max_length=150, unique=True, null=True, blank=True)     
    warehouse = models.ForeignKey(Warehouse, related_name='locations', on_delete=models.CASCADE)  
    address= models.TextField(null=True,blank=True)  
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.location_id:
            self.location_id = f"LOCID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

from operations.models import ExistingOrder,OperationsRequestOrder
from repairreturn.models import ScrappedOrder
from purchase.models import Batch

class Inventory(models.Model):
    inventory_id = models.CharField(max_length=30,null=True,blank=True) 
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='inventory_user'
    )
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,related_name='batch_inventory',null=True,blank=True)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='warehouse_inventory'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='location_inventory'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_inventories',
        null=True,
        blank=True
    )
    quantity = models.IntegerField(default=0,null=True,blank=True) 
    reorder_level = models.PositiveIntegerField(default=10,null=True,blank=True)
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.inventory_id:
            self.inventory_id= f"INVID-{uuid.uuid4().hex[:8].upper()}"
     
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse}--{self.location}--{self.product.name}--{self.quantity}"



class InventoryTransaction(models.Model):  
    inventory_transaction=models.ForeignKey(Inventory,on_delete=models.CASCADE,null=True, blank=True,related_name='inventory_transaction') 
    transaction_id = models.CharField(max_length=30,null=True,blank=True)    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='inventory_transaction_user')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='batch_inventory_transaction',null=True, blank=True)  # NEW
    sale_unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # NEW
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE,null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,null=True, blank=True)
    transaction_type = models.CharField(
    max_length=20,
    choices=[
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
        ('MANUFACTURE_IN', 'Manufacture IN'),
        ('MANUFACTURE_OUT', 'Manufacture OUT'),
        ('REPLACEMENT_OUT', 'Replacement Out'),
        ('REPLACEMENT_IN', 'Replacement In'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('EXISTING_ITEM_IN', 'Existing items'),
        ('OPERATIONS_OUT', 'Operations out'),
        ('SCRAPPED_OUT', 'Scrapped out'),
        ('SCRAPPED_IN','Scrapped in')
    ],
    null=True, blank=True
    )    
    quantity = models.PositiveIntegerField(null=True, blank=True)
    transaction_date = models.DateTimeField(auto_now_add=True)       
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='purchase_transactions', null=True, blank=True, on_delete=models.CASCADE)
    sales_order = models.ForeignKey(SaleOrder, related_name='sale_transactions', null=True, blank=True, on_delete=models.CASCADE)
    manufacture_order = models.ForeignKey(MaterialsRequestOrder,related_name='manufacure_inventory',null=True,blank=True, on_delete=models.CASCADE)
    existing_items_order = models.ForeignKey(ExistingOrder,related_name='Existing_items_inventory',null=True,blank=True, on_delete=models.CASCADE)
    operations_request_order = models.ForeignKey(OperationsRequestOrder,related_name='operations_request_order_inventory',null=True,blank=True, on_delete=models.CASCADE)
    scrapped_order = models.ForeignKey(ScrappedOrder,related_name='scrapped_order_inventory',null=True,blank=True, on_delete=models.CASCADE)
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id= f"INVTID-{uuid.uuid4().hex[:8].upper()}"
     
        super().save(*args, **kwargs)
   
    # def update_inventory(self):
    #     try:          
           
    #         inventory = Inventory.objects.filter(warehouse=self.warehouse, location=self.location, product=self.product).first()
    #         if not inventory:
    #             raise ValueError(f"Inventory record not found for {self.product.name} in {self.warehouse.name} at {self.location.name}.")
            
    #         if self.transaction_type in ['INBOUND', 'TRANSFER_IN', 'EXISTING_ITEM_IN', 'MANUFACTURE', 'REPLACEMENT_IN']:
    #             inventory.quantity += self.quantity
    #         elif self.transaction_type in ['OUTBOUND', 'TRANSFER_OUT', 'REPLACEMENT_OUT', 'OPERATIONS_OUT']:
    #             print('inventory.quantity=', inventory.quantity, 'self.quantity=', self.quantity)
    #             if inventory.quantity < self.quantity:
    #                 raise ValueError(f"Insufficient stock for {self.product.name} in {self.warehouse.name}")
    #             inventory.quantity -= self.quantity
    #         else:
    #             raise ValueError(f"Invalid transaction type: {self.transaction_type}")
            
    #         inventory.save()
    #         self.inventory = inventory
    #         self.save()

    #         return True

    #     except ValueError as ve:
    #         logger.error(f"Inventory update failed: {ve}")
    #         return False
    #     except Exception as e:
    #         logger.error(f"Unexpected error updating inventory: {e}")
    #         return False


    def clean(self):  
        selected_orders = [self.purchase_order, self.sales_order, self.manufacture_order]
        if sum(1 for order in selected_orders if order is not None) > 1:
            raise ValidationError("Only one of purchase_order, sales_order, or manufacture_order should be selected.")

    def __str__(self):       
        return f"{self.transaction_id}-{self.transaction_type}-{self.product}-{self.quantity}"



class TransferOrder(models.Model):
    order_number = models.CharField(max_length=20, unique=True)
    order_status = models.CharField(max_length=20)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='transfer_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.order_number
    


class TransferItem(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True,related_name='transfer_user')
    transfer_order = models.ForeignKey(TransferOrder, related_name='transfers', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch=models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_transfer')
    source_warehouse = models.ForeignKey(Warehouse, related_name='source_transfers', on_delete=models.CASCADE, null=True, blank=True)
    target_warehouse = models.ForeignKey(Warehouse, related_name='target_transfers', on_delete=models.CASCADE, null=True, blank=True)
    source_location = models.ForeignKey(Location, related_name='source_locations', on_delete=models.CASCADE, null=True, blank=True)
    target_location = models.ForeignKey(Location, related_name='target_locations', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(null=True, blank=True)    

    def __str__(self):
        return f"{self.quantity} nos {self.product.name} transferred from {self.source_warehouse.name} to {self.target_warehouse.name}"


from accounts.models import CustomUser

class ReorderLevel(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reorder_levels',null=True,blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='reorder_warehouse',null=True,blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='reorder_location',null=True,blank=True)
    reorder_level = models.PositiveIntegerField(null=True,blank=True)
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True,related_name='reorder_user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reorder level for {self.product.product_name} - {self.warehouse.warehouse_name} is {self.reorder_level}"

    class Meta:
        unique_together = ('product', 'warehouse')  




