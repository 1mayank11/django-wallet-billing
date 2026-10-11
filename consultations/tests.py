from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

# Create your tests here.

from user_accounts.models import RechargeTransaction
from user_accounts.services import process_successful_recharge

from rest_framework.test import APIClient
from django.urls import reverse

from decimal import Decimal

from django.contrib.auth import get_user_model

from user_accounts.models import Wallet, UserProfile
from .models import ConsultationSession, SessionBilling
from .services import bill_next_minute


User = get_user_model()


class SessionBillingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.provider = User.objects.create_user(
            username="testprovider",
            password="testpassword123",
        )

        UserProfile.objects.create(
            user=self.user,
            role="USER",
        )
        UserProfile.objects.create(
            user=self.provider,
            role="PROVIDER",
        )

        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("100.00"),
        )

        
        self.session = ConsultationSession.objects.create(
            user=self.user,
            provider=self.provider,
            status="in_progress",
            price_per_minute=Decimal("10.00"),
            started_at=timezone.now() - timedelta(minutes=2),
        )


    def test_billing_deducts_elapsed_minutes(self):
        session = bill_next_minute(self.session.id)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("80.00"))
        self.assertEqual(session.billed_minutes, 2)
        self.assertEqual(session.total_amount, Decimal("20.00"))
        self.assertEqual(
            SessionBilling.objects.filter(session=session).count(),
            2,
        )

    def test_insufficient_balance_ends_session_without_deduction(self):
        self.wallet.balance = Decimal("5.00")
        self.wallet.save()

        session = bill_next_minute(self.session.id)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5.00"))
        self.assertEqual(session.status, "completed")
        self.assertEqual(session.ended_by, "system")
        self.assertEqual(session.end_reason, "Insufficient balance")
        self.assertEqual(session.billed_minutes, 0)
        self.assertEqual(
            SessionBilling.objects.filter(session=session).count(),
            session.billed_minutes,
        )

        self.assertEqual(
            sum(
                SessionBilling.objects.filter(session=session)
                .values_list("amount", flat=True),
                start=Decimal("0.00"),
            ),
            session.total_amount,
        )

    
    
    def test_repeated_call_does_not_charge_same_minutes_twice(self):
        bill_next_minute(self.session.id)
        bill_next_minute(self.session.id)

        self.wallet.refresh_from_db()

        # Two elapsed minutes cost ₹20, not ₹40.
        self.assertEqual(self.wallet.balance, Decimal("80.00"))

        self.assertEqual(
            SessionBilling.objects.filter(session=self.session).count(),
            2,
        )

        self.session.refresh_from_db()
        self.assertEqual(self.session.billed_minutes, 2)
        self.assertEqual(self.session.total_amount, Decimal("20.00"))

    
    
    def test_insufficient_balance_preserves_previous_billing_totals(self):
        self.wallet.balance = Decimal("20.00")
        self.wallet.save()

        # First bill the two elapsed minutes: ₹20 total.
        session = bill_next_minute(self.session.id)

        self.wallet.refresh_from_db()
        session.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertEqual(session.billed_minutes, 2)
        self.assertEqual(session.total_amount, Decimal("20.00"))

        # Simulate another elapsed minute.
        session.started_at = timezone.now() - timedelta(minutes=3)
        session.save(update_fields=["started_at"])

        # The next minute is unaffordable, so the system must end the session.
        session = bill_next_minute(session.id)
        session.refresh_from_db()

        self.wallet.refresh_from_db()

        self.assertEqual(session.status, "completed")
        self.assertEqual(session.ended_by, "system")
        self.assertEqual(session.end_reason, "Insufficient balance")
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertEqual(session.billed_minutes, 2)
        self.assertEqual(session.total_amount, Decimal("20.00"))

        records = SessionBilling.objects.filter(session=session)
        self.assertEqual(records.count(), session.billed_minutes)
        self.assertEqual(
            sum(
                records.values_list("amount", flat=True),
                start=Decimal("0.00"),
            ),
            session.total_amount,
        )

    def test_provider_cannot_accept_in_progress_session(self):
        client = APIClient()
        client.force_authenticate(user=self.provider)

        response = client.post(
            reverse("accept-session", args=[self.session.id])
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"],
            "Only assigned sessions can be accepted.",
        )

        
    def test_complete_session_lifecycle(self):
        client = APIClient()

        # The user creates the session.
        client.force_authenticate(user=self.user)
        self.session.status = "assigned"
        self.session.started_at = None
        self.session.ended_at = None
        self.session.save()

        # Provider accepts the session.
        client.force_authenticate(user=self.provider)
        response = client.post(
            f"/api/consultations/sessions/{self.session.id}/accept/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "accepted_by_provider")

        # User starts the session.
        client.force_authenticate(user=self.user)
        response = client.post(
            f"/api/consultations/sessions/{self.session.id}/start/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "in_progress")

        # End immediately so no full minute should be billed.
        response = client.post(
            f"/api/consultations/sessions/{self.session.id}/end/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("100.00"))


    def test_create_session_rejects_insufficient_starting_balance(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        self.wallet.balance = Decimal("49.00")
        self.wallet.save()

        response = client.post(
            reverse("create-session"),
            {
                "provider_id": self.provider.id,
                "price_per_minute": "10.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient balance", response.data["error"])


    def test_create_session_rejects_second_active_session(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        # The session created in setUp() is already in progress.
        response = client.post(
            reverse("create-session"),
            {
                "provider_id": self.provider.id,
                "price_per_minute": "10.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("active consultation session", response.data["error"])



    
    def test_create_session_with_sufficient_balance(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Remove the existing active session for this test scenario.
        self.session.status = "completed"
        self.session.save(update_fields=["status"])

        response = client.post(
            reverse("create-session"),
            {
                "provider_id": self.provider.id,
                "price_per_minute": "10.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "assigned")
        self.assertEqual(
            Decimal(response.data["price_per_minute"]),
            Decimal("10.00"),
        )

            
    def test_unassigned_provider_cannot_accept_session(self):
        another_provider = User.objects.create_user(
            username="another_provider",
            password="testpassword123",
        )
        UserProfile.objects.create(
            user=another_provider,
            role="PROVIDER",
        )

        client = APIClient()
        client.force_authenticate(user=another_provider)

        # The session belongs to self.provider, not another_provider.
        response = client.post(
            reverse("accept-session", args=[self.session.id])
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["error"],
            "Only the assigned provider can accept this session.",
        )

        
    def test_recharge_and_session_billing_happy_path(self):
        # Recharge the user's wallet by ₹50.
        recharge = RechargeTransaction.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            reference="INTEGRATION-RECHARGE-001",
            status="pending",
        )
        process_successful_recharge(recharge.reference)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("150.00"))

        # Create a fresh session through the API.
        self.session.status = "completed"
        self.session.save(update_fields=["status"])

        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.post(
            reverse("create-session"),
            {
                "provider_id": self.provider.id,
                "price_per_minute": "10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        session_id = response.data["id"]

        # Provider accepts the session.
        client.force_authenticate(user=self.provider)
        response = client.post(
            reverse("accept-session", args=[session_id])
        )
        self.assertEqual(response.status_code, 200)

        # User starts the session.
        client.force_authenticate(user=self.user)
        response = client.post(
            reverse("start-session", args=[session_id])
        )
        self.assertEqual(response.status_code, 200)

        # Set the start time two minutes in the past to test billing.
        session = ConsultationSession.objects.get(id=session_id)
        session.started_at = timezone.now() - timedelta(minutes=2)
        session.save(update_fields=["started_at"])

        response = client.post(
            reverse("bill-session-minute", args=[session_id])
        )
        self.assertEqual(response.status_code, 200)

        session.refresh_from_db()
        self.wallet.refresh_from_db()

        self.assertEqual(session.billed_minutes, 2)
        self.assertEqual(session.total_amount, Decimal("20.00"))
        self.assertEqual(self.wallet.balance, Decimal("130.00"))
        self.assertEqual(
            SessionBilling.objects.filter(session=session).count(), 2
        )
