from django.db import models

from product.models import Product
from inventory.models import Warehouse
from logistics.models import PurchaseShipment,SaleShipment
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from inventory.models import Location,Inventory
from accounts.models import CustomUser


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type=models.CharField(max_length=255,null=True,blank=True,choices=[
        ('PURCHASE-NOTIFICATION','Purchase notification'),
        ('SALES-NOTIFICATION','Sales Notification'),
        ('PRODUCTION-NOTIFICATION','Production notification'),
        ('GENERAL-NOTIFICATION','General Notification'),
        ('SHIPMENT-NOTIFICATION','Shipment Notification'),
        ('RETURN-NOTIFICATION','Return Notification'),
        ('APPRAISAL-NOTIFICATION','Appraisal Notification'),
        ('OPERATIONS-NOTIFICATION','Appraisal Notification'),
        ('TICKET-NOTIFICATION','Ticket Notification'),
        ('TASK-NOTIFICATION','Task Notification'),
        ('TRANSPORT-NOTIFICATION','Transport Notification'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  

    def __str__(self):
        return f"{self.message} - {'Read' if self.is_read else 'Unread'}"


class ArchivedNotification(models.Model):
    message  = models.TextField()
    created_at = models.DateTimeField()
    archived_on = models.DateTimeField(auto_now_add=True)





class InventoryReport(models.Model):
    inventory=models.ForeignKey(Inventory,on_delete=models.CASCADE,related_name='inventory_report',null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='inventory_report_user')
    report_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Report for {self.inventory}"


class SaleShipmentReport(models.Model):
    sale_shipment = models.ForeignKey(SaleShipment, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='sale_shipment_report_user')
    report_date = models.DateField(auto_now_add=True)  
    total_dispatch = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_pending = models.PositiveIntegerField(default=0)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"Report for {self.sale_shipment.tracking_number}-{self.report_date}"


class PurchaseShipmentReport(models.Model):   
    purchase_shipment = models.ForeignKey(PurchaseShipment, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_shipment_report_user')
    report_date = models.DateField(auto_now_add=True)  
    total_dispatch = models.PositiveIntegerField(default=0)
    total_delivered = models.PositiveIntegerField(default=0)
    total_pending = models.PositiveIntegerField(default=0)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"Report for { self.purchase_shipment.tracking_number} on {self.report_date}"


