from django import forms
from .models import TransportRequest, ManagerApproval,Transport

from.models import Vehiclefault
from.models import FuelRefill
from .models import TransportUsage
from django import forms
from .models import TransportRequest

from django import forms
from .models import TransportRequest
from.models import VehicleRentalCost
from.models import FuelPumpDatabase
from.models import FuelPumpPayment

from .models import TransportExtension


class CreateTransportForm(forms.ModelForm):
    last_maintenance_date = forms.DateTimeField(label='last maintenance date', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})) 
    vehicle_registration_date = forms.DateTimeField(label='vehicle registration date', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))     
    class Meta:
        model = Transport
        exclude = ['vehicle_code','vehicle_mileage']
        widgets = {
            
            'vehicle_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter a description', 
                'rows': 3
            }),
             'vehicle_owner_address': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter a description', 
                'rows': 3
            }),
        }
       
        


class TransportRequestForm(forms.ModelForm):    
    request_datetime = forms.DateTimeField(label='request datetime', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})) 
    return_datetime = forms.DateTimeField(label='return datetime', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})) 
    
    class Meta:
        model = TransportRequest
        fields = ['vehicle','transport_type','item_description', 'request_datetime', 'return_datetime', 'purpose']
        widgets = {
            'item_description': forms.Textarea(attrs={
                'row': 2,
                'class':'form-control',
                'style':'height:30px'
                }),  
              
           
        }    
        


class ManagerApprovalForm(forms.ModelForm):
    class Meta:
        model = ManagerApproval
        fields = ['status','approved_at', 'rejection_reason']
        widgets={
            'approved_at':forms.DateTimeInput(attrs={'type':'datetime-local'}),
        }



class TransportExtensionForm(forms.ModelForm):
    class Meta:
        model = TransportExtension
        fields = ['requested_until', 'reason']
        widgets={
            'requested_until':forms.DateTimeInput(attrs={'type':'datetime-local'})
        }

  
class TransportExtensionApprovaltForm(forms.ModelForm):   
    class Meta:
        model = TransportExtension
        fields =['approval_status','extended_until','cancellation_reason']
        widgets={
            'extended_until':forms.DateTimeInput(attrs={'type':'datetime-local'})
        }
        

from.models import PenaltyPayment 
class PenaltyPaymentForm(forms.ModelForm):
    class Meta:
        model= PenaltyPayment
        fields=['penalty','paid_amount','paid_at','payment_doc']
        widgets={
            'paid_at':forms.DateInput(attrs={'type':'date'})
            
            
        }



class TransportUsageForm(forms.ModelForm):
    class Meta:
        model = TransportUsage
        fields = [
            'booking',
            'travel_date',
            'start_time',
            'end_time',
            'start_location', 
            'end_location',            
            'start_reading',
            'end_reading',          
            'status',
        ]
        widgets = {
            'travel_date': forms.DateInput(attrs={'type': 'date'}),  
            'start_time': forms.TimeInput(attrs={'type': 'time'}),  
            'end_time': forms.TimeInput(attrs={'type': 'time'}),    
        }

      


class TransportRequestStatusUpdateForm(forms.ModelForm):
    status = forms.ChoiceField(choices=[('COMPLETED', 'Completed'), ('IN-USE', 'In Use')])

    class Meta:
        model = TransportRequest
        fields = ['status']  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

         

class TransportilterForm(forms.Form):
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

 
    vehicle_registration_number = forms.CharField(
        label='Vehicle Reg.Number',
        required=False,
       
    )   

    vehicle_code = forms.CharField(
        label='Vehicle Reg.Number',
        required=False,
       
    )  
    status = forms.ChoiceField(choices=[('ALL','All'),('AVAILABLE','Available'),('IN-USE','In use'),('BOOKED','Booked')],
        label='select ',
        required=False,
       
    )  

    
class FuelRefillForm(forms.ModelForm):     
    
    class Meta:
        model = FuelRefill
        exclude = ['fuel_refill_code','vehicle_total_fuel_reserve','refill_requester',
                   'vehicle_kilometer_run','vehicle_fuel_consumed',
                   'vehicle_fuel_balance','created_at','fuel_cost'
                   ]   
        widgets = {
            'fuel_supplier_address': forms.Textarea(attrs={
                'row': 2,
                'class':'form-control',
                'style':'height:100px'
                }),  
                'refill_date': forms.DateInput(attrs={'type': 'date'}),  
           
        }    


    def clean_refill_date(self):
        refill_date = self.cleaned_data['refill_date']
        if not refill_date:
            raise forms.ValidationError("Refill date is required.")
        return refill_date
    


class VehicleFaulttForm(forms.ModelForm):
    fault_start_time = forms.DateTimeField(label='Fault Time', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    fault_stop_time = forms.DateTimeField(label='Fault End Time', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
      
    class Meta:
        model = Vehiclefault
        fields = ['vehicle', 'fault_start_time','fault_stop_time','fault_type','fault_location']


class VehiclePaymentForm(forms.ModelForm):   
    class Meta:
        model = VehicleRentalCost
        exclude = ['vehicle_rent_paid_id','vehicle_total_paid']
        widgets = {
            'paid_at': forms.DateInput(attrs={'type': 'date'}),  
            'comments':forms.Textarea(attrs={
                'row':2,
                'class':'form-control',
                'placeholder': 'Enter a comments', 
                'style':'height:100px'
            })
            
        }



class FuelPumpDatabaseForm(forms.ModelForm):
    contact_date = forms.DateField(label='contact date', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = FuelPumpDatabase
        exclude =['created_at','fuel_pump_id','pump_code']    
        widgets={
            'fuel_pump_address':forms.Textarea(attrs={
            'style':'height:100px'
            })
        }


class viewFuelPumpForm(forms.Form):     
    fuel_pump_name = forms.CharField(required=False)  


class FuelWithdrawForm(forms.Form):    
    start_date = forms.DateField(label='Start Date', widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='End Date', widget=forms.DateInput(attrs={'type': 'date'}))


class FuelPumpSearchForm(forms.Form):
    fuel_pump_name = forms.CharField(label='Fuel Pump Name', max_length=100)
    start_date = forms.DateField(label='Start Date', widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='End Date', widget=forms.DateInput(attrs={'type': 'date'}))



class FuelPumpPaymentForm(forms.ModelForm):   
    class Meta:
        model = FuelPumpPayment
        exclude =['created_at','payment_id']   
        widgets={
            'paid_at':forms.DateTimeInput(attrs={'type':'datetime-local'})
        } 



class PGRViewForm(forms.Form):
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

  

    user_name = forms.CharField(
        label='User Name',    
        required=False
    )





MONTH_CHOICES = [
        ('',''),
        ('JANUARY', 'January'),
        ('FEBRUARY', 'February'),
        ('MARCH', 'March'),
        ('APRIL', 'April'),
        ('MAY', 'May'),
        ('JUNE', 'June'),
        ('JULY', 'July'),
        ('AUGUST', 'August'),
        ('SEPTEMBER', 'September'),
        ('OCTOBER', 'October'),
        ('NOVEMBER', 'November'),
        ('DECEMBER', 'December'),
    ]

class vehicleSummaryReportForm(forms.Form):
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
  

    vehicle_number = forms.CharField(
        label='Vehicle Number',
        required=False,
     
    )

    
    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        label='Month',
        required=False,
     
    )

    year = forms.IntegerField(        
        label='Year',
        required=False,
     
    )
    
