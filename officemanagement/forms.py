from django import forms

from supplier.models import Supplier
from inventory.models import Warehouse,Location

from.models import StationaryUsageRequestOrder,StationaryBatch,StationaryPurchaseOrder,StationaryCategory,StationaryProduct
from .models import MeetingRoomBooking,MeetingOrder,Attendees
from.models import ExpenseSubmissionOrder,ExpenseSubmissionItem,OfficeAdvance,MeetingRoom
from.models import ITSupportTicket,VisitorGroup,VisitorLog,OfficeDocument




class AddCategoryForm(forms.ModelForm):  
    class Meta:
        model = StationaryCategory
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea(attrs=
            {'placeholder': 'Enter your description here...',          
                         
             })
        }
        

class AddProductForm(forms.ModelForm):   
    class Meta:
        model = StationaryProduct
        exclude=['user','product_id']
        widgets = {
            'description': forms.Textarea(attrs=
            {'placeholder': 'Enter your description here...',           
            
             
             })
        }



class CreateProductBatchForm(forms.ModelForm):   
    class Meta:
        model = StationaryBatch
        exclude=['user','batch_number']



class BatchForm(forms.ModelForm):
    class Meta:
        model =StationaryBatch
        exclude=['user','remaining_quantity']

      


class StationaryPurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = StationaryPurchaseOrder  
        fields = ['stationary_category', 'stationary_product','batch','quantity','supplier']  

    stationary_category = forms.ModelChoiceField(
        queryset=StationaryCategory.objects.all(),
        label="Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    stationary_product = forms.ModelChoiceField(
        queryset=StationaryProduct.objects.all(),
        label="Product",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
  
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        label="Supplier",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    batch = forms.ModelChoiceField(
        queryset=StationaryBatch.objects.all(),
        label="Batch",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
  



class StationaryUsageOrderForm(forms.ModelForm):
    class Meta:
        model = StationaryUsageRequestOrder
        fields = ['department', 'stationary_category', 'stationary_product', 'batch', 'quantity']
        exclude = ['purpose']  


    stationary_category = forms.ModelChoiceField(
        queryset=StationaryCategory.objects.all(),
        label="Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    stationary_product = forms.ModelChoiceField(
        queryset=StationaryProduct.objects.all(),
        label="Product",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
  
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )   

    batch = forms.ModelChoiceField(
        queryset=StationaryBatch.objects.all(),
        label="Batch",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
  
  




from django.forms import inlineformset_factory
from .models import StationaryPurchaseOrder, StationaryPurchaseItem
from .models import StationaryUsageRequestOrder, StationaryUsageRequestItem

class StationaryPurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = StationaryPurchaseOrder
        fields = ['supplier', 'order_date']
        widgets={
            'order_date':forms.DateInput(attrs={'type':'date'})
        }

class StationaryPurchaseItemForm(forms.ModelForm):
    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Unit Price",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter unit price'})
    )
    class Meta:
        model = StationaryPurchaseItem
        fields = ['stationary_category', 'stationary_product', 'batch', 'quantity']


StationaryPurchaseItemFormSet = inlineformset_factory(
    StationaryPurchaseOrder,
    StationaryPurchaseItem,
    form=StationaryPurchaseItemForm,
    extra=1,
    can_delete=True
)




class StationaryUsageRequestOrderForm(forms.ModelForm):
    class Meta:
        model = StationaryUsageRequestOrder
        fields = ['department']

class StationaryUsageRequestItemForm(forms.ModelForm):
    class Meta:
        model = StationaryUsageRequestItem
        fields = ['stationary_category', 'stationary_product', 'batch', 'quantity']

# Inline formset for multiple items
StationaryUsageRequestItemFormSet = inlineformset_factory(
    StationaryUsageRequestOrder,
    StationaryUsageRequestItem,
    form=StationaryUsageRequestItemForm,
    extra=1,
    can_delete=True
)







  
class PurchaseRequestInvoiceAddForm(forms.ModelForm):
    class Meta:
        model = StationaryPurchaseOrder
        fields=['invoice_number','invoice_file']
    



class WarehouseSelectionForm(forms.Form):
    product = forms.ModelChoiceField(queryset=StationaryProduct.objects.all(), widget=forms.HiddenInput())
    quantity = forms.IntegerField(widget=forms.HiddenInput())
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all(), label="Select Warehouse")
    location = forms.ModelChoiceField(queryset=Location.objects.all(), label="Select Location")



class MeetingRoomForm(forms.ModelForm):
    class Meta:
        model = MeetingRoom
        exclude=['user']




class MeetingRoomBookingForm(forms.ModelForm):
    class Meta:
        model = MeetingRoomBooking
        fields = ["meeting_ref","date", "start_time", "end_time", "purpose"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "purpose": forms.Textarea(attrs={"rows": 2}),
            
          
        }


class MeetingOrderForm(forms.ModelForm):
    class Meta:
        model = MeetingOrder
        exclude=['order_id','user']
        widgets = {
            "meeting_date": forms.DateInput(attrs={"type": "date"}),
            "meeting_start_time": forms.TimeInput(attrs={"type": "time"}),
            "meeting_end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 2}),
            
          
        }



class AddAttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendees
        exclude = ['user']



class ITSupportForm(forms.ModelForm):
    class Meta:
        model = ITSupportTicket
        fields = ['issue']
        widgets={
            'issue':forms.Textarea(attrs={
                'row':3,
                 'style':'height:150px',
                'class':'form-control'
            })
        }



class ITSupportUpdateForm(forms.ModelForm):
    class Meta:
        model = ITSupportTicket
        fields = ['status','solution_description','resolved_by','resolved_date']
        widgets = {
            "resolved_date": forms.DateInput(attrs={"type": "date"}),
           
        }




class VisitorGroupForm(forms.ModelForm):
    class Meta:
        model = VisitorGroup
        exclude=['user']
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "datetime-local"}),
            "check_out": forms.DateInput(attrs={"type": "datetime-local"}),
            'expected_check_in_time':forms.DateInput(attrs={"type": "datetime-local"}),
            'purpose':forms.Textarea(attrs={
                'row':1,
                'style':'height:50px',
                'class':'form-control'
            })

           
        }


class VisitorLogForm(forms.ModelForm):
    class Meta:
        model = VisitorLog
        exclude=['user','check_out']
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "datetime-local"}),
            "check_out": forms.DateInput(attrs={"type": "datetime-local"}),   
             "company": forms.Select(attrs={"class": "form-control", "placeholder": "Select a company"}),                   
           
               }


from django.forms import inlineformset_factory
from .models import VisitorGroup, VisitorLog,VisitorIDCard

class VisitorGroupCheckInForm(forms.ModelForm):
    class Meta:
        model = VisitorGroup
        fields = ['company', 'address', 'purpose']
        widgets = {           
            'address':forms.TextInput(attrs={'style':'height:80px','class':'form-control'}),
            'purpose':forms.TextInput(attrs={'style':'height:80px','class':'form-control'})
        }

class VisitorMemberForm(forms.ModelForm):
    class Meta:
        model = VisitorLog
        fields = ['name', 'designation', 'visitor_type','id_card', 'phone','photo']
        widgets = {
            'visitor_type': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.TimeInput(attrs={'type': 'time'}),
            'photo':forms.FileInput(attrs={
                'accept': 'image/*',
                'capture': 'camera',
            })
            
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter id_card to only idle ones
        self.fields['id_card'].queryset = VisitorIDCard.objects.filter(status='idle')
        self.fields['id_card'].empty_label = "Select ID Card"

VisitorMemberFormSet = inlineformset_factory(
    VisitorGroup,
    VisitorLog,
    form=VisitorMemberForm,
    extra=2,
    can_delete=True
)


class VisitorSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        label="Search Visitor",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter name or phone number or company or id-card"}),
    )



class ExpenseAdvanceForm(forms.ModelForm):
    class Meta:
        model =  OfficeAdvance
        fields=['purpose','amount','estimated_reimbursement_date']
        widgets={
            'estimated_reimbursement_date':forms.DateInput(attrs={"type": "date"}),
        }

class ExpenseAdvanceApprovalForm(forms.ModelForm):
    class Meta:
        model = OfficeAdvance
        fields=['status','approved_on']
        widgets={
            'approved_on':forms.DateInput(attrs={"type": "date"}),
        }


class ExpenseSubmissionOrderForm(forms.ModelForm):
    class Meta:
        model = ExpenseSubmissionOrder
        exclude=['submission_id','approved_by','approved_on','status','user','submitted_by']
        widgets={
            'submission_date':forms.DateInput(attrs={"type": "date"}),
        }

        
    def clean_advance_ref(self):
        advance_ref = self.cleaned_data.get('advance_ref')

        if advance_ref and ExpenseSubmissionOrder.objects.filter(advance_ref=advance_ref).exists():
            raise forms.ValidationError("An ExpenseSubmissionOrder already exists for this advance reference.")

        return advance_ref
    


class ExpenseSubmissionOrderUpdateForm(forms.ModelForm):
    class Meta:
        model = ExpenseSubmissionOrder
        fields=['status','approved_on']
        widgets={
            'approved_on':forms.DateInput(attrs={"type": "date"}),
        }



class ExpenseSubmissionItemForm(forms.ModelForm):
    class Meta:
        model = ExpenseSubmissionItem
        exclude=['user']
    





from django.forms import inlineformset_factory
from .models import ExpenseSubmissionOrder, ExpenseSubmissionItem

class ExpenseSubmissionOrderForm(forms.ModelForm):
    class Meta:
        model = ExpenseSubmissionOrder
        fields = ['has_advance', 'advance_ref', 'submission_date']
        widgets = {
            'submission_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'has_advance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'advance_ref': forms.Select(attrs={'class': 'form-select'}),
        }

class ExpenseSubmissionItemForm(forms.ModelForm):
    class Meta:
        model = ExpenseSubmissionItem
        fields = ['category', 'amount', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
        }

ExpenseSubmissionItemFormSet = inlineformset_factory(
    ExpenseSubmissionOrder,
    ExpenseSubmissionItem,
    form=ExpenseSubmissionItemForm,
    extra=1,
    can_delete=True
)





class OfficeDocumentForm(forms.ModelForm):
    class Meta:
        model = OfficeDocument
        exclude=['user','uploaded_by']
  

  
