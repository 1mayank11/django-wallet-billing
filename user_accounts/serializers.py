
from rest_framework import serializers

from .models import RechargeTransaction
from decimal import Decimal


class RechargeRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )


class RechargeCallbackSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(
        choices=["success", "failed"],
    )


class RechargeTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RechargeTransaction
        fields = [
            "id",
            "amount",
            "reference",
            "status",
            "created_at",
        ]
        read_only_fields = fields
