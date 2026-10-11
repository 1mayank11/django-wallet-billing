
from django.urls import path

from . import views

urlpatterns = [
    path("wallet/recharge/", views.create_recharge, name="create-recharge"),
    path(
        "wallet/recharge/callback/",
        views.recharge_callback,
        name="recharge-callback",
    ),
]
