from io import BytesIO

import qrcode
import qrcode.image.svg
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import Project


def _project_for(user, pk):
    return get_object_or_404(
        Project.objects.select_related("organization"),
        pk=pk,
        organization__memberships__user=user,
    )


@login_required
@require_GET
def preview_qr(request, pk):
    project = _project_for(request.user, pk)
    target = f"{project.preview_url}?preview=1&v={project.version}"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(target)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    response = HttpResponse(output.getvalue(), content_type="image/svg+xml")
    response["Cache-Control"] = "private, max-age=60"
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    response["X-Content-Type-Options"] = "nosniff"
    return response
