
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Wallet, RechargeTransaction
from .services import process_successful_recharge


User = get_user_model()


class RechargeCallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recharge_test_user",
            password="testpassword123",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("100.00"),
        )

        self.recharge = RechargeTransaction.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            reference="TEST-RECHARGE-001",
            status="pending",
        )

    def test_duplicate_successful_callback_credits_wallet_once(self):
        process_successful_recharge(self.recharge.reference)
        process_successful_recharge(self.recharge.reference)

        self.wallet.refresh_from_db()
        self.recharge.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("150.00"))
        self.assertEqual(self.recharge.status, "success")
        self.assertEqual(
            RechargeTransaction.objects.filter(
                reference=self.recharge.reference
            ).count(),
            1,
        )
