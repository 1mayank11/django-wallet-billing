
from decimal import Decimal

from rest_framework import serializers
from .models import ConsultationSession


class CreateSessionSerializer(serializers.Serializer):
    provider_id = serializers.IntegerField(min_value=1)
    price_per_minute = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )


class ConsultationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationSession
        fields = [
            "id",
            "user",
            "provider",
            "status",
            "price_per_minute",
            "started_at",
            "ended_at",
            "billed_minutes",
            "total_amount",
            "ended_by",
            "end_reason",
            "created_at",
        ]
        read_only_fields = fields
