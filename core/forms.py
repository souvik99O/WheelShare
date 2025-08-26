from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    USER_TYPE_CHOICES = [
        ('renter', 'I want to rent a cycle'),
        ('owner', 'I want to rent out my cycle')
    ]
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),label="What would you like to do?")
    class Meta:
        model = User
        fields = ['username','email', 'password1', 'password2', 'user_type']


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
