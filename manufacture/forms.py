
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
  


from purchase.models import Batch
class MaterialsDeliveryForm(forms.ModelForm):
    class Meta:
        model = MaterialsDeliveryItem
        fields = [
            'materials_request_order',
            'materials_request_item',
            'category',
            'product',
            'product_type',
            'batch',
            'quantity',
            'warehouse',
            'location',
        ]

    materials_request_order = forms.ModelChoiceField(
        queryset=MaterialsRequestOrder.objects.all(),
        label="Materials Request Order",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    materials_request_item = forms.ModelChoiceField(
        queryset=MaterialsRequestItem.objects.all(),
        label="Materials Request Item",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

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
            ('BOM', 'BOM'),
        ],
        label="Product Type",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),
        label="Batch",
        required=False,
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

    def __init__(self, *args, request_instance=None, item_instance=None, **kwargs):
        """
        request_instance -> MaterialsRequestOrder object
        item_instance -> MaterialsRequestItem object (optional)
        """
        super().__init__(*args, **kwargs)

        # Narrow down order queryset
        if request_instance:
            self.fields['materials_request_order'].queryset = MaterialsRequestOrder.objects.filter(id=request_instance.id)
            self.fields['materials_request_item'].queryset = MaterialsRequestItem.objects.filter(material_request_order=request_instance)

        # Populate form with initial values if an item instance is given
        if item_instance:
            self.fields['materials_request_item'].initial = item_instance
            self.fields['quantity'].initial = item_instance.quantity

            if item_instance.product:
                product = item_instance.product
                self.fields['product'].initial = product
                self.fields['category'].initial = product.category
                self.fields['product_type'].initial = getattr(product, 'product_type', None)

                # ✅ Only show batches for this product
                self.fields['batch'].queryset = Batch.objects.filter(product=product)
                # If the order item already has a batch assigned
                if getattr(item_instance, 'batch_id', None):
                    self.fields['batch'].initial = item_instance.batch

        # Add truncation style for dropdowns
        for field_name in ['materials_request_order', 'materials_request_item']:
            self.fields[field_name].widget.attrs.update({
                'style': 'max-width: 250px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
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
        fields = ['warehouse', 'location', 'product', 'quantity', 'batch', 'remarks']
        widgets = {           
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


from django.forms import inlineformset_factory

FinishedGoodsFormSet = inlineformset_factory(
    MaterialsRequestOrder,
    FinishedGoodsReadyFromProduction,
    form=FinishedGoodsForm,
    extra=1,
    can_delete=True
)


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
