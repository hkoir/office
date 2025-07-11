
from django import forms
from.models import InventoryTransaction,Warehouse,Location,TransferItem
from product.models import Product




class AddWarehouseForm(forms.ModelForm):      
    class Meta:
        model = Warehouse
        exclude = ['created_at','updated_at','history','user','warehouse_id','reorder_level','lead_time']
        widgets = {
            
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter a description', 
                'rows': 3
            }),
        }

class AddLocationForm(forms.ModelForm):      
    class Meta:
        model = Location
        fields= ['warehouse','name','address','description']
        widgets = {
            'address': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter the address', 
                'rows': 3
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter a description', 
                'rows': 3
            }),
        }

          



class InventoryTransactionForm  (forms.ModelForm):
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
        model = InventoryTransaction
        exclude = ['user','created_at','updated_at','history']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),            
        }


from purchase.models import Batch

class QualityControlCompletionForm(forms.Form):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        label="Select Warehouse",
        required=True
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),  # Initially empty, will be dynamically loaded
        label="Select Location",
        required=True
    )  
    # batch= forms.ModelChoiceField(
    #     queryset=Batch.objects.all(),  # Initially empty, will be dynamically loaded
    #     label="Select Batch",
    #     required=False
    # )  

    def __init__(self, *args, **kwargs): 
        warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
        
        if warehouse:
            self.fields['location'].queryset = Location.objects.filter(warehouse=warehouse)



class TransferProductForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    source_warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all())
    target_warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all())
    source_location = forms.ModelChoiceField(queryset=Location.objects.all())
    target_location = forms.ModelChoiceField(queryset=Location.objects.all())
    quantity = forms.IntegerField(min_value=1)

    remarks = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3,
                'style': 'height: 40px;', 
            }
        )
    )

    class Meta:
        model=TransferItem
        exclude=['transfer_order','user']
        widgets={
            'batch':forms.Select(attrs={
                'class':'form-control'
            })
        }

    
# Form for filtering by transaction type and product
class TransactionFilterForm(forms.Form):
    transaction_type_choices=[
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
        ('MANUFACTURE_IN', 'Manufacture IN'),
        ('MANUFACTURE_OUT', 'Manufacture OUT'),
        ('REPLACEMENT_OUT', 'Replacement Out'),
        ('REPLACEMENT_IN', 'Replacement In'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('EXISTING_ITEM_IN', 'Existing items'),
        ('OPERATIONS_OUT', 'Operations out'),
        ('SCRAPPED_OUT', 'Scrapped out'),
        ('SCRAPPED_IN','Scrapped in'),
    ]
    transaction_type = forms.ChoiceField(choices=transaction_type_choices, required=True)
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=True)

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
   


from .models import Inventory

class WarehouseReorderLevelForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['product', 'warehouse', 'reorder_level']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
        }
