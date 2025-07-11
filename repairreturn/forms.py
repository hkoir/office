
from django import forms
from .models import ReturnOrRefund
from sales.models import SaleOrder,SaleOrderItem   
from .models import FaultyProduct
from .models import Replacement
from product.models import Product
from inventory.models import Warehouse,Location
from.models import ScrappedItem,RepairReturnCustomerFeedback




class ReturnOrRefundForm(forms.ModelForm):
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3,
                'style': 'height: 30px;width:150px',
            },
        ),
    )

    sale_order = forms.ModelChoiceField(
        queryset=SaleOrder.objects.all(), 
        required=True,
        label="Sale Order",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sale = forms.ModelChoiceField(
        queryset=SaleOrderItem.objects.none(), 
        required=True,
        label="Sold Items",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ReturnOrRefund
        fields = [ 'sale', 'return_reason', 'refund_type', 'quantity_refund', 'remarks']

    def __init__(self, *args, **kwargs):
        sale_order_id = kwargs.pop('sale_order_id', None)  
        super().__init__(*args, **kwargs)

        if sale_order_id:
            self.fields['sale_order'].initial = SaleOrder.objects.get(id=sale_order_id)
            self.fields['sale'].queryset = SaleOrderItem.objects.filter(sale_order_id=sale_order_id)
        else:
            self.fields['sale'].queryset = SaleOrderItem.objects.none()



class RepairReturnCustomerFeedbackForm(forms.ModelForm):
    class Meta:
        model = RepairReturnCustomerFeedback
        exclude=['feedback_id','progress_by_customer','progress_by_user']
        widgets={
            'comments':forms.Textarea(attrs={
                'class':'form-control',
                'row':2,
                'style':'height:100px',
                'placeholder':'Please enter your comment'
            }),
           
        }
      
             

class ReturnOrRefundFormInternal(forms.ModelForm):
    remarks = forms.CharField( required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 4,  
                'style': 'width:350px',  
            },
           
        )
    )  
    processed_date = forms.DateField(
        label='Processed date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = ReturnOrRefund
        exclude = ['created_at','updated_at','product','customer','warehouse','location','quantity_sold','return_id','user' ]




class FaultyProductForm(forms.ModelForm):
    class Meta:
        model = FaultyProduct
        exclude = ['created_at','updated_at','sale','warehouse','location','product','faulty_product_quantity','customer_feedback','user' ]
        widgets = {
            'reason_for_fault': forms.Textarea(attrs={'rows': 3}),
            'inspection_date': forms.DateInput(attrs={'type': 'date'}),
            'resolution_date': forms.DateInput(attrs={'type': 'date'}),
            'resolution_action': forms.Textarea(attrs={'rows': 2}),
            'batch':forms.Select(attrs={'class':'form-control'})
        }
    def __init__(self, *args, **kwargs):  
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Preserve existing widget classes
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f"{existing_classes} form-control".strip()


class ReplacementProductForm(forms.ModelForm):
    class Meta:
        model = Replacement
        fields = ['source_inventory','warehouse','location','batch','quantity','status'] 
       
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)       
            for field in self.fields.values():
                field.widget.attrs.update({'class': 'form-control'})
    



class ScrapProductForm(forms.ModelForm):
    feedback = forms.CharField( required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 2,  
                'style': 'width:250px',  
            },
           
        )
    ) 
    class Meta:
        model = ScrappedItem
        fields = ['scrapped_product','batch','source_inventory','quantity','feedback'] 
       
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)       
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    




class ScrapOrderListForm(forms.Form):
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

 
    order_id = forms.CharField(
        label='Order ID',
        required=False,
       
    )   
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all(),required=False)
    location = forms.ModelChoiceField(queryset=Location.objects.all(),required=False)


class ScrapConfirmationForm(forms.ModelForm):
    class Meta:
        model = ScrappedItem 
        fields = ['scrapped_order', 'scrapped_product','batch', 'warehouse', 'location', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)       
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
