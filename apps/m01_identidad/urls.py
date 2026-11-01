from django.urls import path

from apps.m01_identidad.views import LoginView, LogoutView, ProfileView, TokenRefreshView

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("profile", ProfileView.as_view(), name="auth-profile"),
]

