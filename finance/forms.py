
from django import forms
from .models import PurchaseInvoice, PurchasePayment,SaleInvoice,SalePayment
from purchase.models import PurchaseOrder
from.models import SaleInvoiceAttachment,SalePaymentAttachment,PurchasePaymentAttachment,PurchaseInvoiceAttachment




class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        fields = ['purchase_shipment', 'amount_due','VAT_rate','VAT_type','AIT_rate','AIT_type']
        widgets = {
            'purchase_shipment': forms.Select(attrs={'class': 'form-control'}),
            'issued_date': forms.DateInput(attrs={'type': 'Date'}),
            'amount_due': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'VAT_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'VAT Rate (%)'}),
            'VAT_type': forms.Select(attrs={'class': 'form-control'}),
            'AIT_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'AIT Rate (%)'}),
            'AIT_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_shipment'].label = "Purchase shipment"
        self.fields['amount_due'].label = "Amount Due"
      



class PurchaseInvoiceAttachmentForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoiceAttachment
        fields = ['file']



class PurchasePaymentForm(forms.ModelForm):
    class Meta:
        model = PurchasePayment
        fields = ['purchase_invoice', 'amount', 'payment_method']
        widgets = {
            'purchase_invoice': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Payment Amount'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(PurchasePaymentForm, self).__init__(*args, **kwargs)
        self.fields['purchase_invoice'].label = "Invoice"
        self.fields['amount'].label = "Payment Amount"
        self.fields['payment_method'].label = "Payment Method"



class PurchasePaymentAttachmentForm(forms.ModelForm):
    class Meta:
        model = PurchasePaymentAttachment
        fields = ['file']

        

class SaleInvoiceForm(forms.ModelForm):
    class Meta:
        model = SaleInvoice
        fields = ['sale_shipment', 'amount_due','VAT_rate','VAT_type','AIT_rate','AIT_type',]
        widgets = {
            'sale_shipment': forms.Select(attrs={'class': 'form-control'}),
            'amount_due': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'VAT_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'VAT Rate (%)'}),
            'VAT_type': forms.Select(attrs={'class': 'form-control'}),
            'AIT_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'AIT Rate (%)'}),
            'AIT_type': forms.Select(attrs={'class': 'form-control'}),
            
        }

    def __init__(self, *args, **kwargs):
        super(SaleInvoiceForm, self).__init__(*args, **kwargs)
        self.fields['sale_shipment'].label = "sale shipment"
        self.fields['amount_due'].label = "Amount Due"
     
       




class SaleInvoiceAttachmentForm(forms.ModelForm):
    class Meta:
        model = SaleInvoiceAttachment
        fields = ['file']


class SalePaymentForm(forms.ModelForm):
    class Meta:
        model = SalePayment
        fields = ['sale_invoice', 'amount', 'payment_method']
        widgets = {
            'sale_invoice': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Payment Amount'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(SalePaymentForm, self).__init__(*args, **kwargs)
        self.fields['sale_invoice'].label = "Invoice"
        self.fields['amount'].label = "Amount"
        self.fields['payment_method'].label = "Payment Method"


class SalePaymentAttachmentForm(forms.ModelForm):
    class Meta:
        model = SalePaymentAttachment
        fields = ['file']