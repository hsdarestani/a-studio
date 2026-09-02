from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import Project
from .services.source_import import SourceImportError, normalize_source_url

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
    BACKEND_CHOICES = [
        ("auth", _("Authentication — managed & available")),
        ("database", _("Database — managed & available")),
        ("storage", _("File storage — managed & available")),
        ("push", _("Push notifications — architecture ready")),
        ("subscriptions", _("Subscriptions / paywall — architecture ready")),
    ]
    backend_features = forms.MultipleChoiceField(
        label=_("Backend kit"),
        choices=BACKEND_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Authentication, owner-scoped database and private file storage are live in A+ Managed Backend. Push and subscriptions stay architecture-ready until their external providers are configured."),
    )

    class Meta:
        model = Project
        fields = (
            "name",
            "business_type",
            "description",
            "language",
            "source_type",
            "source_url",
            "builder_mode",
            "backend_features",
        )
        labels = {
            "name": _("App name"),
            "business_type": _("Business type"),
            "description": _("Business context and desired outcome"),
            "language": _("App language"),
            "source_type": _("Start from"),
            "source_url": _("Source URL"),
            "builder_mode": _("Builder engine"),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": _("Describe the business, target users and what the app should do.")}),
            "language": forms.Select(choices=[("de", "Deutsch"), ("en", "English")]),
            "source_type": forms.RadioSelect,
            "source_url": forms.URLInput(attrs={"placeholder": "https://github.com/company/project or https://example.com"}),
        }
        help_texts = {
            "source_url": _("Required only for GitHub or website import. Private GitHub repositories work when Studio has repository access."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_type"].required = False
        self.fields["builder_mode"].required = False
        self.fields["source_type"].initial = self.initial.get("source_type", "prompt")
        self.fields["builder_mode"].initial = self.initial.get("builder_mode", "safe_pwa")
        self.fields["builder_mode"].choices = [
            ("safe_pwa", _("Safe PWA Builder")),
            ("code_agent", _("Code Agent V3 — real code workspace")),
        ]
        self.fields["builder_mode"].help_text = _(
            "Code Agent V3 edits real HTML/CSS/JavaScript files with revision snapshots and live preview. Executable framework builds use the isolated sandbox when configured."
        )

    def clean_source_type(self):
        return self.cleaned_data.get("source_type") or "prompt"

    def clean_builder_mode(self):
        value = self.cleaned_data.get("builder_mode") or "safe_pwa"
        allowed = {str(item[0]) for item in self.fields["builder_mode"].choices}
        return value if value in allowed else "safe_pwa"

    def clean_source_url(self):
        source_type = self.cleaned_data.get("source_type") or "prompt"
        try:
            return normalize_source_url(self.cleaned_data.get("source_url", ""), source_type)
        except SourceImportError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_backend_features(self):
        allowed = [value for value, _label in self.BACKEND_CHOICES]
        requested = [item for item in self.cleaned_data.get("backend_features", []) if item in allowed]
        if any(item in requested for item in ("database", "storage", "push", "subscriptions")) and "auth" not in requested:
            requested.insert(0, "auth")
        return [item for item in allowed if item in requested]
