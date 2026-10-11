from django.db import models

# Create your models here.

from django.conf import settings

class ConsultationSession(models.Model):
    STATUS_CHOICES = [
        ("unassigned", "Unassigned"),
        ("assigned", "Assigned"),
        ("accepted_by_provider", "Accepted by provider"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consultation_sessions",
    )

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_sessions",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="unassigned",
    )

    price_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    billed_minutes = models.PositiveIntegerField(default=0)

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
    )

    ended_by = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    end_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} - {self.status}"


  # billing history


class SessionBilling(models.Model):
    session = models.ForeignKey(
        ConsultationSession,
        on_delete=models.CASCADE,
        related_name="billing_records",
    )

    minute_number = models.PositiveIntegerField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    billed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "minute_number"],
                name="unique_session_billed_minute",
            )
        ]
        ordering = ["minute_number"]

    def __str__(self):
        return (
            f"Session {self.session_id} - "
            f"Minute {self.minute_number} - ₹{self.amount}"
        )
