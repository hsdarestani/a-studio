from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .mobile_api import _delete_user_data


def _legal_context():
    return {
        "contact_email": settings.BILLING_CONTACT_EMAIL,
        "company_name": "A+ Solution GmbH",
        "app_name": "A+ Studio",
    }


def privacy(request):
    return render(request, "legal/privacy.html", _legal_context())


def terms(request):
    return render(request, "legal/terms.html", _legal_context())


def support(request):
    return render(request, "legal/support.html", _legal_context())


@require_http_methods(["GET", "POST"])
def account_deletion(request):
    context = _legal_context()
    if request.method == "POST":
        if request.user.is_authenticated:
            if request.POST.get("confirmation", "").upper() != "DELETE":
                messages.error(request, "Bitte bestätigen Sie die Löschung mit DELETE.")
                return redirect("account_deletion")
            with transaction.atomic():
                _delete_user_data(request.user)
            return render(request, "legal/account_deleted.html", context)

        email = request.POST.get("email", "").strip().lower()
        if not email:
            messages.error(request, "Bitte geben Sie die E-Mail-Adresse Ihres A+ Studio Kontos an.")
            return redirect("account_deletion")
        send_mail(
            subject="A+ Studio – Antrag auf Kontolöschung",
            message=(
                "Ein Nutzer hat über die öffentliche A+ Studio Löschseite die Löschung "
                f"des Kontos {email} angefordert. Bitte Identität prüfen und den Antrag bearbeiten."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.BILLING_CONTACT_EMAIL],
            fail_silently=False,
        )
        context["requested_email"] = email
        return render(request, "legal/account_deletion_requested.html", context)
    return render(request, "legal/account_deletion.html", context)
