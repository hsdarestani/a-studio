from django.urls import path

from . import legal_views, mobile_api, sandbox_views, views, workflow_views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("health/", views.health, name="health"),

    # Public legal/support URLs used by App Store Connect and Google Play.
    path("privacy/", legal_views.privacy, name="privacy"),
    path("datenschutz/", legal_views.privacy, name="privacy_de"),
    path("terms/", legal_views.terms, name="terms"),
    path("nutzungsbedingungen/", legal_views.terms, name="terms_de"),
    path("support/", legal_views.support, name="support"),
    path("account-deletion/", legal_views.account_deletion, name="account_deletion"),
    path("konto-loeschen/", legal_views.account_deletion, name="account_deletion_de"),

    # First-party native A+ Studio API. Authentication uses short-lived signed
    # bearer tokens; Capacitor origins are handled directly by mobile_endpoint.
    path("api/mobile/config/", mobile_api.config, name="mobile_config"),
    path("api/mobile/login/", mobile_api.login, name="mobile_login"),
    path("api/mobile/signup/", mobile_api.signup, name="mobile_signup"),
    path("api/mobile/me/", mobile_api.me, name="mobile_me"),
    path("api/mobile/dashboard/", mobile_api.dashboard, name="mobile_dashboard"),
    path("api/mobile/projects/", mobile_api.project_create, name="mobile_project_create"),
    path("api/mobile/projects/<uuid:pk>/", mobile_api.project_detail, name="mobile_project_detail"),
    path("api/mobile/projects/<uuid:pk>/chat/", mobile_api.chat, name="mobile_chat"),
    path(
        "api/mobile/projects/<uuid:pk>/messages/<uuid:message_id>/",
        mobile_api.message_status,
        name="mobile_message_status",
    ),
    path("api/mobile/projects/<uuid:pk>/publish/", mobile_api.publish, name="mobile_publish"),
    path(
        "api/mobile/projects/<uuid:pk>/store-submission/",
        mobile_api.request_store_submission,
        name="mobile_store_submission",
    ),
    path("api/mobile/account/delete/", mobile_api.account_delete, name="mobile_account_delete"),

    # Isolated Code Agent service callback. The endpoint is CSRF-exempt but
    # authenticates the raw request body with a shared HMAC signature.
    path("api/sandbox/runs/<uuid:run_id>/callback/", sandbox_views.sandbox_callback, name="sandbox_callback"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<uuid:pk>/", views.project_detail, name="project_detail"),
    path("projects/<uuid:pk>/status/", views.project_status, name="project_status"),
    path("projects/<uuid:pk>/chat/", workflow_views.chat_submit, name="chat_submit"),
    path(
        "projects/<uuid:pk>/messages/<uuid:message_id>/",
        workflow_views.message_status,
        name="message_status",
    ),
    path("projects/<uuid:pk>/publish/", views.publish_project, name="publish_project"),
    path("projects/<uuid:pk>/spec/", views.export_spec, name="export_spec"),
    path("projects/<uuid:pk>/download/", views.download_build, name="download_build"),
    path(
        "projects/<uuid:pk>/store-submission/",
        workflow_views.request_store_submission,
        name="request_store_submission",
    ),
    path(
        "projects/<uuid:pk>/store-submissions/",
        workflow_views.store_submissions,
        name="store_submissions",
    ),
    path("billing/", views.billing, name="billing"),
    path("api/tls/allow/", views.tls_allow, name="tls_allow"),
]
