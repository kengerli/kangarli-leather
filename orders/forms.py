from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        # Fields that the user will fill out
        fields = ['first_name', 'last_name', 'email', 'city', 'address']
        
        # We add Bootstrap CSS classes directly here so the HTML template stays clean
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Baku'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full street address'}),
        }