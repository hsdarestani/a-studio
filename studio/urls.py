from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from core import views
from core.forms import EmailAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/login/", auth_views.LoginView.as_view(authentication_form=EmailAuthenticationForm), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/", include("allauth.urls")),
    path("", include("core.urls")),
]
