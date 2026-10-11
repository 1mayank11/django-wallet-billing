
from decimal import Decimal


from .services import bill_next_minute

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user_accounts.models import Wallet, UserProfile
from .models import ConsultationSession
from .serializers import (
    CreateSessionSerializer,
    ConsultationSessionSerializer,
)

User = get_user_model()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_session(request):
    serializer = CreateSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    provider_id = serializer.validated_data["provider_id"]
    price = serializer.validated_data["price_per_minute"]

    if price <= Decimal("0.00"):
        return Response(
            {"error": "Price per minute must be greater than zero."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        provider = User.objects.get(pk=provider_id)
    except User.DoesNotExist:
        return Response(
            {"error": "Provider not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        profile = provider.profile
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Selected user is not a provider."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if profile.role != "PROVIDER":
        return Response(
            {"error": "Selected user is not a provider."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if provider == request.user:
        return Response(
            {"error": "You cannot book a session with yourself."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.balance < price * 5:
            return Response(
                {
                    "error": (
                        "Insufficient balance. You need at least "
                        "five minutes of session charges to start."
                    ),
                    "required_balance": str(price * 5),
                    "current_balance": str(wallet.balance),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_statuses = [
            "unassigned",
            "assigned",
            "accepted_by_provider",
            "in_progress",
        ]

        if ConsultationSession.objects.filter(
            user=request.user,
            status__in=active_statuses,
        ).exists():
            return Response(
                {"error": "You already have an active consultation session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = ConsultationSession.objects.create(
            user=request.user,
            provider=provider,
            status="assigned",
            price_per_minute=price,
        )

    return Response(
        ConsultationSessionSerializer(session).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_session(request, session_id):
    with transaction.atomic():
        try:
            session = ConsultationSession.objects.select_for_update().get(
                pk=session_id
            )
        except ConsultationSession.DoesNotExist:
            return Response(
                {"error": "Consultation session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.provider_id != request.user.id:
            return Response(
                {"error": "Only the assigned provider can accept this session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if session.status != "assigned":
            return Response(
                {"error": "Only assigned sessions can be accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.status = "accepted_by_provider"
        session.save(update_fields=["status"])

    return Response(ConsultationSessionSerializer(session).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request, session_id):
    with transaction.atomic():
        try:
            session = ConsultationSession.objects.select_for_update().get(
                pk=session_id
            )
        except ConsultationSession.DoesNotExist:
            return Response(
                {"error": "Consultation session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.user_id != request.user.id:
            return Response(
                {"error": "Only the user who booked the session can start it."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if session.status != "accepted_by_provider":
            return Response(
                {"error": "Only accepted sessions can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.status = "in_progress"
        session.started_at = timezone.now()
        session.save(update_fields=["status", "started_at"])

    return Response(ConsultationSessionSerializer(session).data)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bill_session_minute(request, session_id):
    try:
        session = ConsultationSession.objects.get(pk=session_id)
    except ConsultationSession.DoesNotExist:
        return Response(
            {"error": "Consultation session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check authorization before any billing operation.
    if (
        session.user_id != request.user.id
        and session.provider_id != request.user.id
    ):
        return Response(
            {"error": "Only the session user or assigned provider can bill it."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        session = bill_next_minute(session_id)
    except ConsultationSession.DoesNotExist:
        return Response(
            {"error": "Consultation session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Wallet.DoesNotExist:
        return Response(
            {"error": "User wallet not found."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(ConsultationSessionSerializer(session).data)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    try:
        with transaction.atomic():
            session = ConsultationSession.objects.select_for_update().get(
                pk=session_id
            )

            if (
                session.user_id != request.user.id
                and session.provider_id != request.user.id
            ):
                return Response(
                    {
                        "error": (
                            "Only the session user or assigned provider "
                            "can end it."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if session.status != "in_progress":
                return Response(
                    {"error": "Only in-progress sessions can be ended."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Record the end time first so billing uses the final duration.
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])

            session = bill_next_minute(session.id)

            # Insufficient funds may already have completed the session.
            if session.status == "completed":
                return Response(ConsultationSessionSerializer(session).data)

            session.status = "completed"
            session.ended_by = (
                "user" if session.user_id == request.user.id else "provider"
            )
            session.end_reason = "Ended by " + session.ended_by
            session.save(
                update_fields=[
                    "status",
                    "ended_by",
                    "end_reason",
                ]
            )

    except ConsultationSession.DoesNotExist:
        return Response(
            {"error": "Consultation session not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    except Wallet.DoesNotExist:
        return Response(
            {"error": "User wallet not found."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(ConsultationSessionSerializer(session).data)
