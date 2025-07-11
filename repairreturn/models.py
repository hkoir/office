from django.db import models

from accounts.models import User
from product.models import Product
from customer.models import Customer
from inventory.models import Warehouse,Location

from sales.models import SaleOrder,SaleOrderItem
from purchase.models import PurchaseOrder,PurchaseOrderItem
from django.apps import apps
import uuid
from accounts.models import CustomUser
from purchase.models import Batch

class ReturnOrRefund(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True, related_name='return_or_refund_user')
    return_id = models.CharField(max_length=20,null=True, blank=True)
    sale = models.ForeignKey(SaleOrderItem,null=True, blank=True, related_name='sale_returns', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,null=True,blank=True)
    customer = models.ForeignKey(Customer, related_name='customer_return_refund', on_delete=models.CASCADE,null=True,blank=True)
    warehouse = models.ForeignKey(Warehouse, related_name='return_refund_warehouses', on_delete=models.CASCADE,null=True,blank=True)
    location = models.ForeignKey(Location, related_name='return_refund_locations', on_delete=models.CASCADE,null=True,blank=True)
    quantity_sold = models.PositiveIntegerField(null=True, blank=True)       
    return_reason = models.CharField(max_length=20, choices=[
        ('DEFECTIVE', 'DEFECTIVE'),
        ('NOT_AS_DESCRIBED', 'NOT AS DESCRIBED'),
        ('OTHER', 'OTHER'),
    ],null=True, blank=True,)
    refund_type = models.CharField(max_length=20, choices=[
        ('FULL', 'Full Refund'),
        ('PARTIAL', 'Partial Refund'),
    ],null=True, blank=True,)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'PENDING'),
        ('Acknowledged', 'Acknowledged'),
        ('REJECTED', 'REJECTED'),
    ], default='PENDING',null=True, blank=True,)
   
    quantity_refund = models.PositiveIntegerField(null=True, blank=True)
    requested_date = models.DateTimeField(auto_now_add=True,null=True)
    processed_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    processed_date = models.DateTimeField(null=True, blank=True)
    progress_by_customer = models.FloatField(default=0,null=True, blank=True)  
    progress_by_user = models.FloatField(default=0,null=True, blank=True)  
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

    def save(self, *args, **kwargs):
        if not self.warehouse and self.sale.warehouse:
            self.warehouse = self.sale.warehouse
        if not self.location and self.sale.location:
            self.location = self.sale.location
        if not self.product and self.sale.product:
            self.product= self.sale.product
        if not self.quantity_sold and self.sale.quantity:
            self.quantity_sold = self.sale.quantity     

        if not self.return_id:
            self.return_id= f"RID-{uuid.uuid4().hex[:8].upper()}"  
        
        super().save(*args,**kwargs)

    def __str__(self):
        return f"{self.quantity_refund} nos {self.sale.product.name} refund applied by customer"

      
class FaultyProduct(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,null=True, blank=True,related_name='user_faulty_product')
    return_request = models.ForeignKey(ReturnOrRefund, on_delete=models.CASCADE, related_name='faulty_products', null=True, blank=True,)
    sale = models.ForeignKey(SaleOrderItem, on_delete=models.CASCADE, related_name='faulty_sales')   
    warehouse = models.ForeignKey(Warehouse, related_name='return_warehouses', on_delete=models.CASCADE,null=True,blank=True)
    location = models.ForeignKey(Location, related_name='return_locations', on_delete=models.CASCADE,null=True,blank=True) 
    product = models.ForeignKey(Product, on_delete=models.CASCADE,null=True, blank=True,)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_faulty_product')
    faulty_product_quantity = models.PositiveIntegerField(null=True, blank=True,)


    reason_for_fault = models.TextField(null=True, blank=True,)
    status = models.CharField(max_length=100, choices=[
        ('UNDER_INSPECTION', 'UNDER INSPECTION'), 
        ('REPAIRABLE', 'REPAIRABLE'), 
        ('UNREPAIRABLE', 'UNREPAIRABLE'),
        ('REPAIRED_AND_READY', 'Repaire and ready'),
        ('REPAIRED_AND_RETURNED','Repaire and returned'),
        ('SCRAPPED', 'SCRAPPED')
    ], default='UNDER_INSPECTION',null=True, blank=True,)
    
    return_status = models.BooleanField(default=False,null=True, blank=True,) 
    repair_quantity = models.PositiveIntegerField(null=True, blank=True)
    return_quantity = models.PositiveIntegerField(null=True, blank=True)
    inspected_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolution_action = models.CharField(max_length=50, null=True, blank=True)
    customer_feedback = models.TextField(null=True, blank=True)
    inspection_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.return_request:
            if not self.product and self.return_request.sale:
                self.product = self.return_request.sale.product
            if not self.faulty_product_quantity:
                self.faulty_product_quantity = self.return_request.quantity_refund
            if not self.warehouse and self.return_request.warehouse:
                self.warehouse = self.return_request.warehouse
            if not self.location and self.return_request.location:
                self.location = self.return_request.location

        super().save(*args, **kwargs)

    def __str__(self):
        return f" {self.faulty_product_quantity} nos faulty {self.sale.product.name} issue raised by customer"



class Replacement(models.Model):
    quantity = models.PositiveIntegerField(null=True, blank=True)
    source_inventory = models.ForeignKey('inventory.Inventory',on_delete=models.CASCADE,related_name='replacement_source_inventory',null=True, blank=True,)    
    faulty_product = models.ForeignKey(FaultyProduct, on_delete=models.CASCADE, related_name='faulty_replacement',null=True,blank=True)
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_replacement')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='replacement_users', null=True, blank=True)
    warehouse=models.ForeignKey(Warehouse,on_delete=models.CASCADE,related_name='replacement_warehouse',null=True, blank=True,)
    location=models.ForeignKey(Location,on_delete=models.CASCADE,related_name='replacement_location',null=True, blank=True,)
    replacement_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='replacement_products', null=True, blank=True)  
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='replacement_customers', null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'PENDING'),
        ('REPLACED_DONE', 'Replaced'),
        ('CANCELLED', 'CANCELLED'),
    ], default='PENDING',null=True, blank=True,)

    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_inventory(self):
            Warehouse = apps.get_model('inventory', 'Inventory')
            return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None


    def save(self, *args, **kwargs):
        if self.faulty_product and not self.replacement_product:
            self.replacement_product = self.faulty_product.product
        if self.faulty_product and self.faulty_product.return_request:
            sale = self.faulty_product.return_request.sale
            if sale and not self.customer:
                self.customer = sale.sale_order.customer
        if self.source_inventory:
            if not self.warehouse:
                self.warehouse = self.source_inventory.warehouse
            if not self.location:
                self.location = self.source_inventory.location
        super().save(*args, **kwargs)
             
    def __str__(self):
        return f"Replacement for {self.faulty_product.product.name} in {self.warehouse.name}"
    


class RepairReturnCustomerFeedback(models.Model):
    feedback_id =models.CharField(max_length=30)
    repair_return = models.ForeignKey(ReturnOrRefund,on_delete=models.CASCADE,null=True,blank=True,related_name='return_feedback')
    is_work_completed = models.BooleanField('Is Work Completed?',default=False,choices=[(False, 'No'), (True, 'Yes')]) 
    progress=models.CharField(max_length=100,choices=
            [                        
                ('PROGRESS-20%','Progress 20%'),
                ('PROGRESS-30%','Progress 30%'),
                ('PROGRESS-40%','Progress 40%'),
                ('PROGRESS-50%','Progress 50%'),
                ('PROGRESS-60%','Progress 60%'),
                ('PROGRESS-70%','Progress 70%'),
                ('PROGRESS-80%','Progress 80%'),
                ('PROGRESS-90%','Progress 90%'),
                ('PROGRESS-100%','Progress 100%'),                             
               
            ], null=True, blank=True
            )
    work_quality_score = models.FloatField(default=0.0,blank=True, null=True)  
    communication_quality_score = models.FloatField(default=0.0,blank=True, null=True) 
    timely_completion_score= models.FloatField(default=0.0,blank=True, null=True)  
    behavoiural_quality_score = models.FloatField(default=0.0,blank=True, null=True)  
    product_quality = models.FloatField(default=0.0,blank=True, null=True)  
    image = models.ImageField(upload_to='repair_return',blank=True, null=True)  
    comments = models.TextField(blank=True, null=True)  

    def save(self, *args, **kwargs):       
        if not self.feedback_id:
            self.feedback_id= f"CFBK-{uuid.uuid4().hex[:8].upper()}"      

        super().save(*args,**kwargs)
           
    def __str__(self):
        return f"Customer_feedback-{self.feedback_id} "





class ScrappedOrder(models.Model):
    order_id = models.CharField(max_length=30)
    STATUS_CHOICES=[
        ('SUBMITTED','Submitted'),
        ('REVIEWED','Reviewed'),
        ('SCRAPPED_OUT','Scrapped out'),
        ('CANCELLED','Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING',null=True,blank=True)  
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks=models.TextField(null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='scrap_user', null=True, blank=True)

    approval_data = models.JSONField(default=dict,null=True,blank=True)
    requester_approval_status = models.CharField(max_length=20, null=True, blank=True)
    reviewer_approval_status = models.CharField(max_length=20, null=True, blank=True)
    approver_approval_status = models.CharField(max_length=20, null=True, blank=True)

    Requester_remarks=models.TextField(null=True,blank=True)
    Reviewer_remarks=models.TextField(null=True,blank=True)
    Approver_remarks=models.TextField(null=True,blank=True)

    def save(self, *args, **kwargs):       
        if not self.order_id:
            self.order_id= f"SCRAID-{uuid.uuid4().hex[:8].upper()}"  
        super().save(*args,**kwargs)

           
    def __str__(self):
        return f"Scrapped order-{self.order_id} "



class ScrappedItem(models.Model):
    scrapped_item_id =models.CharField(max_length=30)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='scrap_item_user', null=True, blank=True)
    scrapped_order = models.ForeignKey(ScrappedOrder,on_delete=models.CASCADE,null=True,blank=True,related_name='scrap_request_items')
    scrapped_product =models.ForeignKey(Product, on_delete=models.CASCADE, related_name='scrapped_product')
    batch = models.ForeignKey(Batch,on_delete=models.CASCADE,null=True,blank=True,related_name='batch_scrap')
    quantity = models.PositiveIntegerField(null=True, blank=True)
    source_inventory = models.ForeignKey('inventory.Inventory',on_delete=models.CASCADE,related_name='scrapped_source_inventory',null=True, blank=True,)    
   
    warehouse=models.ForeignKey(Warehouse,on_delete=models.CASCADE,related_name='scrapped_warehouse',null=True, blank=True,)
    location=models.ForeignKey(Location,on_delete=models.CASCADE,related_name='scrapped_location',null=True, blank=True,)
   
   
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'PENDING'),
        ('SUBMITTED', 'Submitted'),
        ('SCRAPPED_OUT', 'Scrapped out'),
        ('COMPLETED', 'COMPLETED'),
    ], default='PENDING',null=True, blank=True,)

    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):       
        if not self.scrapped_item_id:
            self.scrapped_item_id= f"SCITEMID-{uuid.uuid4().hex[:8].upper()}"  
        super().save(*args,**kwargs)


    def get_inventory(self):
        Warehouse = apps.get_model('inventory', 'Inventory')
        return Warehouse.objects.get(id=self.warehouse.id) if self.warehouse else None

             
    def __str__(self):
        return f"Scrapped for {self.scrapped_item_id}"