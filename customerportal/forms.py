
from django import forms
from .models import  TicketCustomerFeedback




class TicketCustomerFeedbackForm(forms.ModelForm):
    class Meta:
        model =  TicketCustomerFeedback
        exclude=['feedback_id']
        widgets={
            'comments':forms.Textarea(attrs={
                'class':'form-control',
                'row':2,
                'style':'height:100px',
                'placeholder':'Please enter your comment'
            }),
           
        }
      


class FilterForm(forms.Form):
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    days = forms.IntegerField(
        label='Number of Days',
        min_value=1,
        required=False
    )

 
    ticket_number = forms.CharField(
        label='Ticket Number',
        required=False,
       
    )   

from sales.models import SaleQualityControl

class QualityControlFormByCustomer(forms.ModelForm):  

    class Meta:
        model = SaleQualityControl
        fields = ['total_quantity', 'good_quantity_by_customer', 'bad_quantity_by_customer', 'inspection_date_by_customer', 'comments_by_customer']
        widgets={
            'inspection_date_by_customer':forms.DateInput(attrs={'type':'date'}),
            'comments_by_customer':forms.Textarea(attrs={
                'class':'form-control',
                'row':2,
                'style':'height:100px',
                'placeholder':'Please enter your comment'
            }),
           

        }


from recruitment.models import Candidate

class CandidateForm(forms.ModelForm):   
    class Meta:
        model = Candidate
        exclude = ['candidate','total_score','cv_screening_score',
                   'exam_score','interview_score','status','cv_screening_status',
                   'exam_status','interview_status','hiring_status',
                   'offer_status','confirmation_status','onboard_status','confirmation_deadline',
                   'joining_date','expected_joining_date','manager_confirmation_of_joining','joining_deadline',
                   'bq_exam_score','bq_exam_status','mcq_bq_score','mcq_bq_exam_status'
                   ]
        widgets = {                  
           
            'language_skill_level': forms.CheckboxSelectMultiple,            
            'experience': forms.CheckboxSelectMultiple,
            'certification': forms.CheckboxSelectMultiple,
            'skills': forms.CheckboxSelectMultiple,
            'education': forms.CheckboxSelectMultiple,
            'subject': forms.CheckboxSelectMultiple,
            'subject_of_education': forms.CheckboxSelectMultiple,
            'institution_of_education': forms.CheckboxSelectMultiple,
            
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) 
        self.fields['age'].required = False
        self.fields['education'].required = False
        self.fields['subject_of_education'].required = False
        self.fields['institution_of_education'].required = False
        self.fields['experience'].required = False
        self.fields['certification'].required = False
        self.fields['skills'].required = False
        self.fields['language_skill_level'].required = False

