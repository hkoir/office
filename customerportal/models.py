from django.db import models
import uuid
from tasks.models import Ticket


from django.utils import timezone

class EmailSubscription(models.Model):  
    email = models.EmailField(unique=True, verbose_name="Email Address")
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)    
    is_active = models.BooleanField(default=False, help_text="Set True once subscriber confirms email")
    subscribed_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)    
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Job Alert Subscriber"
        verbose_name_plural = "Job Alert Subscribers"

    def __str__(self):
        return self.email




def cv_upload_path(instance, filename):   
    return f'cvs/{instance.email}_{filename}'

class JobApplication(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    job_position = models.CharField(max_length=100, blank=True, null=True)
    cv = models.FileField(upload_to=cv_upload_path)
    cover_letter = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"

    def __str__(self):
        return f"{self.full_name} - {self.email}"


class TicketCustomerFeedback(models.Model):    
    feedback_id =models.CharField(max_length=30)   
    ticket = models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name='ticket_feedback_by_customer')
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
            self.feedback_id= f"TCFBK-{uuid.uuid4().hex[:8].upper()}"      

        super().save(*args,**kwargs)
           
    def __str__(self):
        return f"Customer_feedback-{self.feedback_id} "

