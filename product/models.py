
from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
import uuid
from accounts.models import CustomUser


class Category(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='category_user')
    name = models.CharField(max_length=100)
    category_id = models.CharField(max_length=150, unique=True, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
            ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.category_id:
            self.category_id = f"CAT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='product_user')
    name = models.CharField(max_length=255)
    product_id = models.CharField(max_length=150, unique=True, null=True, blank=True)  
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')  # Updated related name
    product_type = models.CharField(max_length=50, 
        choices=[
        ('raw_materials', 'raw_materials'),
        ('finished_product', 'finished_roduct'),
        ('component','component'),
        ('BOM','BOM')
        ], 
        default='finished product')
    brand = models.CharField(max_length=255, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    UOM = models.CharField(max_length=15,null=True,blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True )
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    manufacture_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)  
    warranty = models.DurationField(blank=True, null=True)  
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    reorder_level = models.PositiveIntegerField(default=10,null=True,blank=True)
    lead_time = models.PositiveIntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    product_image= models.ImageField(upload_to='products',null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.product_id:
            self.product_id = f"PID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Component(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='component_user')
    component_id = models.CharField(max_length=150, unique=True, null=True, blank=True)  
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="components")  # Updated related name
    quantity_needed = models.PositiveIntegerField()
    unit_price =models.DecimalField(max_digits=15,decimal_places=2,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.component_id:
            self.component_id = f"CID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
         return self.name



class BOM(models.Model):
    name = models.CharField(max_length=100) 
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='bom_user') 
    bom_id = models.CharField(max_length=150, unique=True, null=True, blank=True) 
    description = models.TextField(blank=True, null=True) 
    product = models.ForeignKey(Product, related_name='bills_of_materials', on_delete=models.CASCADE)
    unit_price =models.DecimalField(max_digits=15,decimal_places=2,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 

    def save(self, *args, **kwargs):
        if not self.bom_id:
            self.bom_id = f"BID-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    






