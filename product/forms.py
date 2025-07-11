from django import forms

from.models import Product,Category



class AddCategoryForm(forms.ModelForm):     

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3, 
                'style': 'height: 20px;', 
            }
        )
    )
 
    class Meta:
        model = Category
        fields = ['name','description']



class AddProductForm(forms.ModelForm):  
    description = forms.CharField(required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control custom-textarea',
                'rows': 3, 
                'style': 'height: 20px;', 
            }
        )
    )    
    manufacture_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    expiry_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = Product
        exclude=['user','product_id']


