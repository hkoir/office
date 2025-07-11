
from django import forms
from product.models import Product,Category
from.models import MaterialsRequestOrder,MaterialsRequestItem,MaterialsDeliveryItem,FinishedGoodsReadyFromProduction,ReceiveFinishedGoods
from .models import ManufactureQualityControl
from inventory.models import Warehouse,Location
from supplier.models import Supplier

from django.contrib.auth.models import User
from accounts.models import CustomUser


class AssignRolesForm(forms.Form):
    requester = forms.ModelChoiceField(queryset=CustomUser.objects.all(), label="Requester")
    reviewer = forms.ModelChoiceField(queryset=CustomUser.objects.all(), label="Reviewer")
    approver = forms.ModelChoiceField(queryset=CustomUser.objects.all(), label="Approver")




class MaterialsRequestForm(forms.ModelForm): 
    class Meta:
        model = MaterialsRequestOrder  
        fields = ['department']  
        widgets = {
            'department': forms.Select(  # Use Select widget for choices
                attrs={
                    'class': 'form-control',
                    'style': 'width:250px;',  # Adjust width using inline CSS
                }
            )
        }

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="Product",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    product_type = forms.ChoiceField(
        choices=[
            ('raw_materials', 'Raw Materials'),
            ('finished_product', 'Finished Product'),
            ('component', 'Component'),
            ('BOM', 'BOM')
        ],
        label="Product Type",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
  



class MaterialsDeliveryForm(forms.ModelForm):
    class Meta:
        model = MaterialsDeliveryItem # Link to the model
        fields = ['materials_request_order', 'materials_request_item']  # Removed redundant `supplier`

    materials_request_order = forms.ModelChoiceField(
        queryset=MaterialsRequestOrder.objects.all(),
        label="Materials Request Order",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    materials_request_item = forms.ModelChoiceField(
        queryset=MaterialsRequestItem.objects.all(),
         label="Materials Request Item",
        required=False)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="Product",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    product_type = forms.ChoiceField(
        choices=[
            ('raw_materials', 'Raw Materials'),
            ('finished_product', 'Finished Product'),
            ('component', 'Component'),
            ('BOM', 'BOM')
        ],
        label="Product Type",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(), 
        label="Warehouse",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),  
        label="Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, request_instance=None, **kwargs):
        super(MaterialsDeliveryForm, self).__init__(*args, **kwargs)
        if request_instance:
            self.fields['materials_request_order'].queryset = MaterialsRequestOrder.objects.filter(id=request_instance.id)
            self.fields['materials_request_item'].queryset = MaterialsRequestItem.objects.filter(material_request_order=request_instance)
            materials_request_item = MaterialsRequestItem.objects.filter(material_request_order=request_instance).first()
            
            if materials_request_item:
                self.fields['quantity'].initial = materials_request_item.quantity
                if materials_request_item.product:
                    product = materials_request_item.product
                    self.fields['product'].initial = product

        else:
            self.fields['materials_request_order'].queryset = MaterialsRequestOrder.objects.all()
            self.fields['materials_request_item'].queryset = MaterialsRequestItem.objects.all()

        self.fields['materials_request_order'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })

        self.fields['materials_request_item'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })


class QualityControlForm(forms.ModelForm):
    comments = forms.CharField(required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 5, 
                'style': 'height: 100px;', 
            }
        )
    )
    inspection_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = ManufactureQualityControl
        fields = ['total_quantity','good_quantity', 'bad_quantity','inspection_date', 'comments']

    def clean(self):
        cleaned_data = super().clean()
        total_quantity = cleaned_data.get("total_quantity")
        good_quantity = cleaned_data.get("good_quantity")
        bad_quantity = cleaned_data.get("bad_quantity")
        
        if good_quantity and bad_quantity and total_quantity:
            if good_quantity + bad_quantity > total_quantity:
                raise forms.ValidationError("Good and bad quantities cannot exceed the total quantity.")
        return cleaned_data


class FinishedGoodsForm(forms.ModelForm):
    class Meta:
        model = FinishedGoodsReadyFromProduction
        fields = ['materials_request_order', 'product', 'quantity','status','remarks']
        widgets = {           
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        request_order_queryset = kwargs.pop('request_order_queryset', None)
        super().__init__(*args, **kwargs)
        if request_order_queryset:
            self.fields['materials_request_order'].queryset = request_order_queryset



class MaterialsOrderSearchForm(forms.Form):
    order_number = forms.CharField(
        label=" Request Order Number",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter order number'})
    )



class MaterialsStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('REVIEWED', 'Reviewed'),
        ('APPROVED', 'Approved'),
        ('CANCELLED', 'Cancelled'),
    ]
    approval_status = forms.ChoiceField(choices=STATUS_CHOICES, widget=forms.Select)

    remarks = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 5, 
                'style': 'height: 100px;', 
            }
        ),
        required=False
    )
