
from django.urls import path
from . import views

urlpatterns = [
    path(
        "sessions/",
        views.create_session,
        name="create-session",
    ),
    path(
        "sessions/<int:session_id>/accept/",
        views.accept_session,
        name="accept-session",
    ),
    path(
    "sessions/<int:session_id>/start/",
    views.start_session,
    name="start-session",
    ),
    path(
        "sessions/<int:session_id>/bill/",
        views.bill_session_minute,
        name="bill-session-minute",
    ),
    path(
    "sessions/<int:session_id>/end/",
    views.end_session,
    name="end-session",
    ),
]
