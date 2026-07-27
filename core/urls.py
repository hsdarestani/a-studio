from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("health/", views.health, name="health"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<uuid:pk>/", views.project_detail, name="project_detail"),
    path("projects/<uuid:pk>/chat/", views.chat_submit, name="chat_submit"),
    path("projects/<uuid:pk>/messages/<uuid:message_id>/", views.message_status, name="message_status"),
    path("projects/<uuid:pk>/publish/", views.publish_project, name="publish_project"),
    path("projects/<uuid:pk>/spec/", views.export_spec, name="export_spec"),
    path("projects/<uuid:pk>/download/", views.download_build, name="download_build"),
    path("projects/<uuid:pk>/store-submission/", views.request_store_submission, name="request_store_submission"),
    path("billing/", views.billing, name="billing"),
    path("billing/checkout/<str:plan>/", views.billing_checkout, name="billing_checkout"),
    path("api/stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("api/tls/allow/", views.tls_allow, name="tls_allow"),
]
