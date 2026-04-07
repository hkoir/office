
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









from django.forms import inlineformset_factory




from django.forms import inlineformset_factory
from .models import DirectInvoice, DirectInvoiceItem,DirectPurchaseInvoice,DirectPurchaseInvoiceItem

class DirectInvoiceForm(forms.ModelForm):
    class Meta:
        model = DirectInvoice
        fields = ["document_type","created_at", "due_date", "customer_name","advance_amount", "discount_amount", "notes","terms_and_conditions"]
        widgets = {
            "created_at": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2, "style": "height:80px;"}),
            "terms_and_conditions": forms.Textarea(attrs={"rows": 2, "style": "height:100px;"}),
        }

class DirectInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = DirectInvoiceItem
        fields = ["product","description","batch","usage_purpose","warehouse","location", "quantity", "unit_price", "total_price"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "any", "class": "form-control quantity-input"}),
            "unit_price": forms.NumberInput(attrs={"step": "any", "class": "form-control unit-price-input"}),
            "total_price": forms.NumberInput(attrs={
                "step": "any", 
                "readonly": "readonly",  # 👈 ensure it's visible but not editable
                "class": "form-control total-price-input"
            }),
             "description": forms.Textarea(attrs={"rows": 2, "style": "height:60px;"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        product = cleaned_data.get("product")
        batch = cleaned_data.get("batch")
        if category and product:
            if product.category_id != category.id:
                raise forms.ValidationError(
                    f"Selected product does not belong to '{category.name}' category."
                )
        if batch and product:
            if batch.product_id != product.id:
                raise forms.ValidationError(
                    f"Batch '{batch.batch_number}' does not belong to selected product '{product.name}'."
                )
        return cleaned_data

DirectInvoiceItemFormSet = inlineformset_factory(
    DirectInvoice,
    DirectInvoiceItem,
    form=DirectInvoiceItemForm,
    extra=1,
    can_delete=True
)



DirectInvoiceItemUpdateFormSet = inlineformset_factory(
    DirectInvoice,
    DirectInvoiceItem,
    form=DirectInvoiceItemForm,
    extra=0,
    can_delete=True
)





class DirectPurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = DirectPurchaseInvoice
        fields = ["created_at", "due_date", "supplier_name", "advance_amount", "discount_amount", "notes","terms_and_conditions"]
        widgets = {
            "created_at": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2, "style": "height:80px;"}),
            "terms_and_conditions": forms.Textarea(attrs={"rows": 2, "style": "height:80px;"}),
        }


class DirectPurchaseInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = DirectPurchaseInvoiceItem
        fields = ["product","description", "batch", "warehouse", "location", "quantity", "unit_price", "total_price"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "any", "class": "form-control quantity-input"}),
            "unit_price": forms.NumberInput(attrs={"step": "any", "class": "form-control unit-price-input"}),
            "total_price": forms.NumberInput(attrs={
                "step": "any",
                "readonly": "readonly",
                "class": "form-control total-price-input",
            }),
            "description": forms.Textarea(attrs={"rows": 2, "style": "height:60px;"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        product = cleaned_data.get("product")
        batch = cleaned_data.get("batch")
        if category and product:
            if product.category_id != category.id:
                raise forms.ValidationError(
                    f"Selected product does not belong to '{category.name}' category."
                )
        if batch and product:
            if batch.product_id != product.id:
                raise forms.ValidationError(
                    f"Batch '{batch.batch_number}' does not belong to selected product '{product.name}'."
                )
        return cleaned_data


DirectPurchaseInvoiceItemFormSet = inlineformset_factory(
    DirectPurchaseInvoice,
    DirectPurchaseInvoiceItem,
    form=DirectPurchaseInvoiceItemForm,
    extra=1,
    can_delete=True
)
