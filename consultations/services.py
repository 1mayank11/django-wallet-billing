
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from user_accounts.models import Wallet
from .models import ConsultationSession, SessionBilling



@transaction.atomic
def bill_next_minute(session_id):
    session = (
        ConsultationSession.objects
        .select_for_update()
        .get(pk=session_id)
    )

    if session.status != "in_progress":
        raise ValueError("Only in-progress sessions can be billed.")

    price = session.price_per_minute
    if price is None or price <= Decimal("0.00"):
        raise ValueError("Session price must be greater than zero.")

    if session.started_at is None:
        raise ValueError("Session start time is missing.")

    now = session.ended_at or timezone.now()
    elapsed_seconds = (now - session.started_at).total_seconds()
    elapsed_minutes = max(0, int(elapsed_seconds // 60))

    wallet = Wallet.objects.select_for_update().get(user=session.user)

    while session.billed_minutes < elapsed_minutes:
        next_minute = session.billed_minutes + 1

        if wallet.balance < price:
            session.billed_minutes = SessionBilling.objects.filter(
                session=session
            ).count()

            session.total_amount = sum(
                SessionBilling.objects.filter(session=session)
                .values_list("amount", flat=True),
                start=Decimal("0.00"),
            )

            session.status = "completed"
            session.ended_at = now
            session.ended_by = "system"
            session.end_reason = "Insufficient balance"

            session.save(
                update_fields=[
                    "status",
                    "ended_at",
                    "ended_by",
                    "end_reason",
                    "billed_minutes",
                    "total_amount",
                ]
            )
            return session

        billing, created = SessionBilling.objects.get_or_create(
            session=session,
            minute_number=next_minute,
            defaults={"amount": price},
        )

        if not created:
            # This minute has already been billed; don't charge it again.
            session.billed_minutes = next_minute
            continue

        Wallet.objects.filter(pk=wallet.pk).update(
            balance=F("balance") - price
        )

        wallet.balance -= price
        session.billed_minutes = next_minute
        session.total_amount += price

    session.save(update_fields=["billed_minutes", "total_amount"])
    return session
