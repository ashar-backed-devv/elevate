from django.db import models
from django.conf import settings
from django.utils import timezone
from content.models import Domain, Course

class FreeTierActivation(models.Model):
    """
    Tracks user's one-time free tier activation.
    A user can only activate once ever, tied to a single domain and course.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    activated_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)  # becomes False when user subscribes to paid tier
    has_consumed = models.BooleanField(default=False)  # ensures they never re-activate free tier

    class Meta:
        unique_together = ('user',)

    def __str__(self):
        return f"FreeTier - {self.user} ({self.domain})"


class DomainSubscription(models.Model):
    """
    Tracks user's paid subscription per domain.
    """
    PLAN_INTERVALS = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    price_id = models.CharField(max_length=255)
    plan_interval = models.CharField(max_length=20, choices=PLAN_INTERVALS)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'domain')

    def __str__(self):
        return f"{self.user} - {self.domain} ({self.status})"


class PaymentHistory(models.Model):
    """
    Optional: Tracks invoices/payments for each subscription period.
    """
    domain_subscription = models.ForeignKey(DomainSubscription, on_delete=models.CASCADE, related_name='payments')
    stripe_invoice_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    paid_at = models.DateTimeField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"Payment - {self.domain_subscription.user} ({self.amount} {self.currency})"
