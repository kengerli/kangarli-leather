from django import forms
from django.contrib.auth.models import User

class UserRegistrationForm(forms.ModelForm):
    # Additional fields for passwords (they are not present in the standard User model in this form)
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password_repeat = forms.CharField(label='Repeat Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_password_repeat(self):
        """
        Validation: Checking that both entered passwords match.
        """
        cd = self.cleaned_data
        if cd['password'] != cd['password_repeat']:
            raise forms.ValidationError('Passwords do not match.')
        return cd['password_repeat']
    
class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']