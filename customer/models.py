from django.db import models
from django.contrib.auth.models import User
import uuid
from simple_history.models import HistoricalRecords
from product.models import Product
from django.apps import apps
from accounts.models import CustomUser



class Customer(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    logo = models.ImageField(upload_to='company_logo/',blank=True, null=True)
    name = models.CharField(max_length=150,null=True,blank=True)
    customer_id = models.CharField(max_length=150, null=True, blank=True)
    contact_person = models.CharField(max_length=255,null=True,blank=True)
    email = models.EmailField(null=True,blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)   
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = f"CUS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.name}" if self.name else "(Unnamed Location)"
    
    

class Location(models.Model):
    name=models.CharField(max_length=20,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, related_name='customer_locations', on_delete=models.CASCADE,null=True,blank=True)
    location_id = models.CharField(max_length=150, null=True, blank=True)
    address = models.TextField(null=True,blank=True)
    city = models.CharField(max_length=100,null=True,blank=True)
    state = models.CharField(max_length=100,null=True,blank=True)
    country = models.CharField(max_length=100,null=True,blank=True)
    postal_code = models.CharField(max_length=20,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def save(self, *args, **kwargs):
        if not self.location_id:
            self.location_id = f"LOC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.name})" if self.name else "(Unnamed Location)"



class CustomerPerformance(models.Model):
    sales_order = models.ForeignKey('sales.SaleOrder', related_name='sale_order_performance', null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)   
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='performance_customer_location', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='performance_customer', null=True, blank=True)
    date = models.DateField(blank=True, null=True)
    total_value = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    delivery_rating= models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], blank=True, null=True)  # 1 to 5 rating
    quality_rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], blank=True, null=True)  # 1 to 5 rating
    on_time_delivery = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], blank=True, null=True)  # 1 to 5 rating
    feedback = models.TextField(blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def get_sale_order(self):
        SaleOrder = apps.get_model('sales', 'SaleOrder')
        return SaleOrder.objects.get(id=self.sales_order.id) if self.sales_order.id else None
    
    def __str__(self):
        return f"{self.location.customer.name} purchase on {self.date}"
