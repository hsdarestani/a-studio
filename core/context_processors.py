from django.conf import settings


def platform_context(request):
    return {
        "APP_PUBLIC_URL": settings.APP_PUBLIC_URL,
        "APP_ROOT_DOMAIN": settings.APP_ROOT_DOMAIN,
    }
