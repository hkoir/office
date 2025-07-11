from django.db import models

from logistics.models import SaleShipment,PurchaseShipment
from simple_history.models import HistoricalRecords
from django.contrib.auth.models import User
import uuid
from accounts.models import CustomUser


class SaleShipmentTracking(models.Model):
    sale_tracking_id=models.CharField(max_length=20,null=True,blank=True)
    sale_shipment = models.ForeignKey(SaleShipment, related_name='sale_shipment_tracking', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='sale_shipment_tack_user')
    status_update = models.CharField(max_length=255,null=True, blank=True)
    update_time = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


           
    def save(self, *args, **kwargs):
        if not self.sale_tracking_id:
            self.sale_tracking_id = f"SID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"Tracking Update for {self.sale_shipment.tracking_number } at {self.update_time}"


class PurchaseShipmentTracking(models.Model):
    purchase_tracking_id=models.CharField(max_length=20,null=True,blank=True)
    purchase_shipment = models.ForeignKey(PurchaseShipment,related_name='purchase_shipment_tracking', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='purchase_shipment_tack_user')
    status_update = models.CharField(max_length=255,null=True, blank=True)
    update_time = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(null=True,blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


            
    def save(self, *args, **kwargs):
        if not self.purchase_tracking_id:
            self.purchase_tracking_id = f"SID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"Tracking Update for {self.purchase_shipment.tracking_number } at {self.update_time}"




