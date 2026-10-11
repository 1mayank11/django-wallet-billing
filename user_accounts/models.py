from django.db import models

# Create your models here.


from django.conf import settings


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
    )

    def __str__(self):
        return f"{self.user} - ₹{self.balance}"




  # for recharge model


class RechargeTransaction(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recharge_transactions",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reference} - {self.amount} - {self.status}"


  # for user provider


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("USER", "User"),
        ("PROVIDER", "Provider"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="USER",
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"
