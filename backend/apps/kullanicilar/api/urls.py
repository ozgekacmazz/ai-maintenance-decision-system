from django.urls import path

from apps.kullanicilar.api.views import (
    AdminKontrolView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("admin-kontrol/", AdminKontrolView.as_view(), name="admin-kontrol"),
]
