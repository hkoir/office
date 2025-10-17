
from django import forms
from .models import PurchaseShipment,SaleShipment,PurchaseDispatchItem,SaleDispatchItem
from purchase.models import PurchaseOrderItem
from sales.models import SaleOrder,SaleOrderItem
from purchase.models import Batch
from .models import SaleDispatchItem, SaleShipment, SaleOrderItem


class PurchaseShipmentForm(forms.ModelForm):
    estimated_delivery = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = PurchaseShipment
        fields = ['carrier', 'tracking_number', 'estimated_delivery']




class SaleShipmentForm(forms.ModelForm):
    estimated_delivery = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    class Meta:
        model = SaleShipment
        fields = ['sales_order','carrier', 'tracking_number', 'estimated_delivery']

    def __init__(self, *args, sale_order=None, **kwargs):
        super(SaleShipmentForm, self).__init__(*args, **kwargs)
        if sale_order:
            self.fields['sales_order'].queryset = SaleOrder.objects.filter(id=sale_order.id)
        else:
            self.fields['sales_order'].queryset = SaleOrder.objects.all()



class PurchaseDispatchItemForm(forms.ModelForm):
    dispatch_date=forms.DateField(
        widget=forms.DateInput(attrs={'type':'date'}),
        required=False
    )
    delivery_date=forms.DateField(
        widget=forms.DateInput(attrs={'type':'date'}),
        required=False
    )

    class Meta:
        model = PurchaseDispatchItem
        exclude=['dispatch_id','user','status','batch']


    def __init__(self, *args, purchase_shipment=None, **kwargs):
        super(PurchaseDispatchItemForm, self).__init__(*args, **kwargs)

        if purchase_shipment:
            self.fields['purchase_shipment'].queryset = PurchaseShipment.objects.filter(id=purchase_shipment.id)            
            self.fields['dispatch_item'].queryset = PurchaseOrderItem.objects.filter(purchase_order__purchase_shipment=purchase_shipment)
        else:
            self.fields['purchase_shipment'].queryset = PurchaseShipment.objects.all()
            self.fields['dispatch_item'].queryset = PurchaseOrderItem.objects.all()
         
        self.fields['purchase_shipment'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })
          
        self.fields['dispatch_item'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })



class SaleDispatchItemForm(forms.ModelForm):
    DISPATCH_STRATEGY_CHOICES = [
        ('FIFO', 'First In, First Out'),
        ('LIFO', 'Last In, First Out'),
    ]
    dispatch_strategy = forms.ChoiceField(
        choices=DISPATCH_STRATEGY_CHOICES, 
        required=True,
        widget=forms.Select(attrs={'style': 'max-width: 200px;'})
    )

    class Meta:
        model = SaleDispatchItem
        exclude = ['dispatch_id', 'user','status','unit_selling_price']
        widgets = {
            'dispatch_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'batch':forms.Select(attrs={'class':'form-control'})
        }

    def __init__(self, *args, sale_shipment=None, dispatch_strategy='FIFO', **kwargs):
        super(SaleDispatchItemForm, self).__init__(*args, **kwargs)

        # Set dispatch strategy dynamically
        self.fields['dispatch_strategy'].initial = dispatch_strategy

        if sale_shipment:
            self.fields['sale_shipment'].queryset = SaleShipment.objects.filter(id=sale_shipment.id)
            self.fields['dispatch_item'].queryset = SaleOrderItem.objects.filter(sale_order__sale_shipment=sale_shipment)
            if 'batch' in self.fields:
                self.fields['batch'].queryset = Batch.objects.filter(sale_shipment=sale_shipment)
        else:
            self.fields['sale_shipment'].queryset = SaleShipment.objects.all()
            self.fields['dispatch_item'].queryset = SaleOrderItem.objects.all()
            if 'batch' in self.fields:
                self.fields['batch'].queryset = Batch.objects.all()

        # Styling for dropdowns
        self.fields['sale_shipment'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })
        self.fields['dispatch_item'].widget.attrs.update({
            'style': 'max-width: 200px; word-wrap: break-word; overflow: hidden; text-overflow: ellipsis;'
        })
