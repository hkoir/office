from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from shop.models import Product,Category
from accounts.models import CustomUser



class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name="product_review_users")
    text = models.TextField()
    rating = models.IntegerField()
    image_one = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_two = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_three = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_four = models.ImageField(upload_to='review_images/', blank=True, null=True)


class CompanyReview(models.Model):
    DELIVERY_QUALITY_CHOICES = (
        ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    PAYMENT_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    COMMUNICATION_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    PRODUCT_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    delivery_quality = models.IntegerField(choices=DELIVERY_QUALITY_CHOICES)
    payment_quality = models.IntegerField(choices=PAYMENT_QUALITY_CHOICES)
    communication_quality = models.IntegerField(choices=COMMUNICATION_QUALITY_CHOICES)
    product_quality = models.IntegerField(choices=PRODUCT_QUALITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    review_text = models.TextField(blank='', null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name="company_review_users")




class AudioModel(models.Model):       
    success_audio = models.FileField(upload_to='audio/', blank=True, null=True)  
    failure_audio = models.FileField(upload_to='audio/', blank=True, null=True)

    welcome_message = models.FileField(upload_to='audio/', blank=True, null=True)  
    account_create_success = models.FileField(upload_to='audio/', blank=True, null=True)
    request_for_logged_in = models.FileField(upload_to='audio/', blank=True, null=True)  
    logged_in_success = models.FileField(upload_to='audio/', blank=True, null=True)
    forget_password = models.FileField(upload_to='audio/', blank=True, null=True)  
    order_placed_success = models.FileField(upload_to='audio/', blank=True, null=True)
    hold_on_message = models.FileField(upload_to='audio/', blank=True, null=True)