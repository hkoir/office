from django import forms
from inventory.models import Warehouse,Location
from product.models import Product
from purchase.models import Batch


class SummaryReportChartForm(forms.Form):
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
   

    warehouse_name = forms.ModelChoiceField(queryset=Warehouse.objects.all(),required=False)
    product_name = forms.ModelChoiceField(queryset=Product.objects.all(),required=False)
    batch = forms.ModelChoiceField(queryset=Batch.objects.all(),required=False)



class NotificationArchieveForm(forms.Form):
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