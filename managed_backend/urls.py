from django.urls import path

from . import views

urlpatterns = [
    path("<slug:slug>/config/", views.config, name="managed_config"),
    path("<slug:slug>/auth/signup/", views.signup, name="managed_signup"),
    path("<slug:slug>/auth/login/", views.login, name="managed_login"),
    path("<slug:slug>/auth/me/", views.me, name="managed_me"),
    path("<slug:slug>/records/<slug:collection>/", views.records, name="managed_records"),
    path("<slug:slug>/records/<slug:collection>/<uuid:record_id>/", views.record_detail, name="managed_record_detail"),
]
