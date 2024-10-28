from django import forms
from django.contrib.auth.forms import UserCreationForm
from App.models import User
from django.contrib.auth import authenticate


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["name", "email", "password1","password2"]