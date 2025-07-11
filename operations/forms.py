from django import forms
from product.models import Category,Product
from.models import ExistingOrder
from inventory.models import Warehouse,Location
from.models import OperationsRequestOrder,OperationsRequestItem,OperationsDeliveryItem
from purchase.models import Batch




class ExistingOrderForm(forms.Form):
   
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

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),  
        label="Batch",
        widget=forms.Select(attrs={'class': 'form-control'})
    )




class OperationsRequestForm(forms.ModelForm):
    class Meta:
        model = OperationsRequestOrder  
        fields = ['category','product','quantity']  

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
   
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    


class OperationsDeliveryForm(forms.ModelForm):
    class Meta:
        model = OperationsDeliveryItem 
        fields = ['product','batch','quantity','operations_request_order', 'operations_request_item','warehouse','location']  

    operations_request_order = forms.ModelChoiceField(
        queryset=OperationsRequestOrder.objects.all(),
        label="Materials Request Order",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    operations_request_item = forms.ModelChoiceField(
        queryset=OperationsRequestItem.objects.all(),
         label="Item ID",
        required=False)
   
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="Product",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    batch = forms.ModelChoiceField(
        queryset=Batch.objects.all(),
        label="Batch",
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
        super(OperationsDeliveryForm, self).__init__(*args, **kwargs)
        if request_instance:
            self.fields['operations_request_order'].queryset = OperationsRequestOrder.objects.filter(id=request_instance.id)
            self.fields['operations_request_item'].queryset = OperationsRequestItem.objects.filter(operations_request_order=request_instance)
            operations_request_item = OperationsRequestItem.objects.filter(operations_request_order=request_instance).first()
            
            if operations_request_item:
                self.fields['quantity'].initial =operations_request_item.quantity
                if operations_request_item.product:
                    product = operations_request_item.product
                    self.fields['product'].initial = product

        else:
            self.fields['operations_request_order'].queryset = OperationsRequestOrder.objects.all()
            self.fields['operations_request_item'].queryset = OperationsRequestItem.objects.all()

        self.fields['operations_request_order'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })

        self.fields['operations_request_item'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })
