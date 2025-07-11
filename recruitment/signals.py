from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Candidate

from decimal import Decimal

@receiver(pre_save, sender=Candidate)
def update_total_score(sender, instance, **kwargs):  
 
    cv_score = instance.cv_screening_score if instance.cv_screening_score is not None else 0
    exam_score = instance.exam_score if instance.exam_score is not None else 0
    interview_score = instance.interview_score if instance.interview_score is not None else 0
   
    instance.total_score = Decimal(cv_score) + Decimal(exam_score) + Decimal(interview_score)
