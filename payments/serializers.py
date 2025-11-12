from rest_framework import serializers
from .models import FreeTierActivation, DomainSubscription, PaymentHistory


class FreeTierActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreeTierActivation
        fields = ['id', 'user', 'domain', 'course', 'activated_at', 'is_active', 'has_consumed']


class DomainSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainSubscription
        fields = [
            'id', 'user', 'domain', 'stripe_customer_id', 'stripe_subscription_id',
            'price_id', 'plan_interval', 'status', 'current_period_start',
            'current_period_end', 'cancel_at_period_end', 'is_active'
        ]


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ['id', 'domain_subscription', 'stripe_invoice_id', 'amount', 'currency', 'paid_at', 'status']
