
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import RechargeTransaction
from .services import process_successful_recharge


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_recharge(request):
    amount = request.data.get("amount")

    if amount is None:
        return Response(
            {"error": "Amount is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = Decimal(str(amount))
    except Exception:
        return Response(
            {"error": "Invalid recharge amount."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not amount.is_finite() or amount <= Decimal("0.00"):
        return Response(
            {"error": "Recharge amount must be greater than zero."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recharge = RechargeTransaction.objects.create(
        user=request.user,
        amount=amount,
        reference=f"RECHARGE-{request.user.id}-{__import__('uuid').uuid4().hex}",
        status="pending",
    )

    return Response(
        {
            "reference": recharge.reference,
            "amount": str(recharge.amount),
            "status": recharge.status,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recharge_callback(request):
    reference = request.data.get("reference")
    callback_status = request.data.get("status")

    if not reference or callback_status not in ["success", "failed"]:
        return Response(
            {"error": "Valid reference and status are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        recharge = get_object_or_404(
            RechargeTransaction.objects.select_for_update(),
            reference=reference,
        )

        if callback_status == "failed":
            if recharge.status == "success":
                return Response(
                    {"error": "Recharge has already succeeded."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            recharge.status = "failed"
            recharge.save(update_fields=["status"])

            return Response(
                {
                    "reference": recharge.reference,
                    "status": recharge.status,
                },
                status=status.HTTP_200_OK,
            )

        try:
            recharge = process_successful_recharge(reference)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return Response(
        {
            "reference": recharge.reference,
            "status": recharge.status,
        },
        status=status.HTTP_200_OK,
    )
