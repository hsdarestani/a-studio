from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Project

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email", "placeholder": "name@company.de"}),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Business email"))
    full_name = forms.CharField(max_length=160, label=_("Full name"))
    company_name = forms.CharField(max_length=160, label=_("Company name"))

    class Meta:
        model = User
        fields = ("full_name", "email", "company_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        name = self.cleaned_data["full_name"].strip()
        parts = name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.email = self.cleaned_data["email"].lower()
        user.username = user.email
        if commit:
            user.save()
        return user


class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "business_type", "description", "language")
        labels = {
            "name": _("App name"),
            "business_type": _("Business type"),
            "description": _("Business context and desired outcome"),
            "language": _("App language"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": _("Describe the business, target users and what the app should do.")}),
            "language": forms.Select(choices=[("de", "Deutsch"), ("en", "English")]),
        }
