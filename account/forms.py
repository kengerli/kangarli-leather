from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password_repeat(self):
        """Check that both passwords match."""
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        if password and password_repeat and password != password_repeat:
            raise forms.ValidationError('Passwords do not match.')
        return password_repeat

    def clean(self):
        """Run Django's AUTH_PASSWORD_VALIDATORS against the chosen password."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password:
            user = User(
                username=cleaned_data.get('username', ''),
                first_name=cleaned_data.get('first_name', ''),
                email=cleaned_data.get('email', ''),
            )
            try:
                validate_password(password, user=user)
            except forms.ValidationError as e:
                self.add_error('password', e)
        return cleaned_data


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email