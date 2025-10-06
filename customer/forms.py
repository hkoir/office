
from django import forms
from.models import Customer,Location
from .models import CustomerPerformance


class AddCustomerForm(forms.ModelForm):   
    class Meta:
        model = Customer
        exclude = ['customer_id']


class AddLocationForm(forms.ModelForm):
   
    address = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3,  # Adjust the number of rows as needed
                'style': 'height: 30px;',  # Set the height directly if needed
            }
        )
    )
    class Meta:
        model=Location
        exclude = ['location_id','created_at','updated_at','user']



class UpdateLocationForm(forms.ModelForm):
    address = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3, 
                'style': 'height: 30px;', 
            }
        )
    )
    class Meta:
        model=Location
        exclude = ['location_id','created_at','updated_at','user']





class CustomerPerformanceForm(forms.ModelForm):
    feedback = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3,
                'style': 'height: 40px;', 
            }
        )
    )
    class Meta:
        model = CustomerPerformance
        exclude = ['user','created_at','updated_at','history']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),            
        }

