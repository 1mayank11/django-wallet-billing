
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import Wallet, RechargeTransaction


@transaction.atomic
def process_successful_recharge(reference):
    """
    Credit a wallet for a successful recharge exactly once.

    Returns the recharge transaction.
    """
    recharge = (
        RechargeTransaction.objects
        .select_for_update()
        .get(reference=reference)
    )

    # Ignore duplicate callbacks after a successful recharge.
    if recharge.status == "success":
        return recharge

    if recharge.status == "failed":
        raise ValueError("A failed recharge cannot be marked successful.")

    if recharge.amount <= Decimal("0.00"):
        raise ValueError("Recharge amount must be greater than zero.")

    # Lock the wallet row while updating its balance.
    wallet, _ = Wallet.objects.get_or_create(user=recharge.user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    Wallet.objects.filter(pk=wallet.pk).update(
        balance=F("balance") + recharge.amount
    )

    recharge.status = "success"
    recharge.save(update_fields=["status"])

    return recharge
