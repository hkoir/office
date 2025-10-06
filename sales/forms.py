
from django import forms
from product.models import Product,Category
from.models import SaleRequestOrder,SaleRequestItem,SaleOrder,SaleQualityControl
from inventory.models import Warehouse,Location
from customer.models import Customer
from purchase.models import Batch

from django.forms import inlineformset_factory
from .models import CustomerQuotation, CustomerQuotationItem




class CustomerQuotationForm(forms.ModelForm):
    class Meta:
        model = CustomerQuotation
        fields = ["customer", "date","valid_until", "status", "notes"]
        widgets={
            'notes':forms.TextInput(attrs={
                'style':'height:50px'
            }),
            'valid_until': forms.DateInput(attrs={'type':'date'}),
             'date': forms.DateInput(attrs={'type':'date'})
        }

class CustomerQuotationItemForm(forms.ModelForm):
    class Meta:
        model = CustomerQuotationItem
        fields = ["product", "quantity", "unit_price", "vat_percentage"]

CustomerQuotationItemFormSet = inlineformset_factory(
    CustomerQuotation,
    CustomerQuotationItem,
    form=CustomerQuotationItemForm,
    extra=1,
    can_delete=True
)




class SaleRequestForm(forms.ModelForm):
    class Meta:
        model = SaleRequestOrder 
        fields = ['category','product','product_type', 'quantity','customer' ]  

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

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        label="Customer",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),
        label="Batch",
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

    unit_selling_price = forms.DecimalField(
        label="Unit Selling Price",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
 
    
    warehouse= forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        label="Warehouse",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    location= forms.ModelChoiceField(
        queryset=Location.objects.all(),
        label="Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )




class SaleOrderForm(forms.ModelForm):
    class Meta:
        model = SaleOrder  
        fields = ['sale_request_order','category', 'product', 'product_type', 'quantity','customer']  # Include fields from your form

    sale_request_order = forms.ModelChoiceField(
        queryset=SaleRequestOrder.objects.all(),
        label="Sale Request Order",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

        
    sale_request_item = forms.ModelChoiceField(
        queryset=SaleRequestItem.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'max-width: 100%; overflow-wrap: break-word;'})
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
    customer= forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        label="Customer",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),
        label="Batch",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    warehouse= forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        label="Warehouse",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    location= forms.ModelChoiceField(
        queryset=Location.objects.all(),
        label="Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    
    unit_selling_price = forms.DecimalField(
        label="Unit Selling Price",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, request_instance=None, **kwargs):
        super(SaleOrderForm, self).__init__(*args, **kwargs)

        if request_instance:
            self.fields['sale_request_order'].queryset = SaleRequestOrder.objects.filter(id=request_instance.id)
            self.fields['sale_request_item'].queryset = SaleRequestItem.objects.filter(sale_request_order=request_instance)
            self.fields['customer'].queryset = Customer.objects.filter(request_customer_sale=request_instance.id)

            if 'initial' not in kwargs:
                self.initial.update({
                    'sale_request_order': request_instance,
                    'customer': request_instance.customer,  
                })
        else:
            self.fields['sale_request_order'].queryset = SaleRequestOrder.objects.all()
            self.fields['sale_request_item'].queryset = SaleRequestItem.objects.all()
            self.fields['customer'].queryset = Customer.objects.all()





class QualityControlForm(forms.ModelForm):
    comments = forms.CharField(
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

    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(), 
        label="Warehouse",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),  
        label="Location",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = SaleQualityControl
        fields = ['total_quantity', 'good_quantity', 'bad_quantity', 'inspection_date', 'comments']


    def __init__(self, *args, initial_warehouse=None, initial_location=None, **kwargs):
        super().__init__(*args, **kwargs)
    
        if initial_warehouse:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(id=initial_warehouse.id)
            self.fields['warehouse'].initial = initial_warehouse

        if initial_location:
            self.fields['location'].queryset = Location.objects.filter(id=initial_location.id)
            self.fields['location'].initial = initial_location

    def clean(self):
        cleaned_data = super().clean()
        total_quantity = cleaned_data.get("total_quantity")
        good_quantity = cleaned_data.get("good_quantity")
        bad_quantity = cleaned_data.get("bad_quantity")

        if good_quantity and bad_quantity and total_quantity:
            if good_quantity + bad_quantity > total_quantity:
                raise forms.ValidationError("Good and bad quantities cannot exceed the total quantity.")
        return cleaned_data
    




    def clean(self):
        cleaned_data = super().clean()
        total_quantity = cleaned_data.get("total_quantity")
        good_quantity_by_customer = cleaned_data.get("good_quantity_by_customer")
        bad_quantity_by_customer = cleaned_data.get("bad_quantity_by_customer")

        if good_quantity_by_customer and bad_quantity_by_customer and total_quantity:
            if good_quantity_by_customer + bad_quantity_by_customer > total_quantity:
                raise forms.ValidationError("Good and bad quantities cannot exceed the total quantity.")
        return cleaned_data




class SaleOrderSearchForm(forms.Form):
    order_number = forms.CharField(
        label="Sale Order Number",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter order number'})
    )


class PurchaseStatusForm(forms.Form):
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




class SalesReportForm(forms.Form):    
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

    product_name = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label='Product',      
        required=False
    )
   
   