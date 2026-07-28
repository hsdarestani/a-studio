from django.conf import settings


def platform_context(request):
    return {
        "APP_PUBLIC_URL": settings.APP_PUBLIC_URL,
        "APP_ROOT_DOMAIN": settings.APP_ROOT_DOMAIN,
        "google_oauth_enabled": bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET),
        "apple_oauth_enabled": bool(
            settings.APPLE_OAUTH_CLIENT_ID
            and settings.APPLE_OAUTH_KEY_ID
            and settings.APPLE_OAUTH_TEAM_ID
            and settings.APPLE_OAUTH_PRIVATE_KEY
        ),
    }
