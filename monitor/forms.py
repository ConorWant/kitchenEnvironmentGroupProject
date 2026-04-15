from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    def clean_email(self):
        email = self.cleaned_data.get("email")
        try:
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError("Enter a valid email address.")
        return email

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
