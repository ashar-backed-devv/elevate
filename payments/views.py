import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import FreeTierActivation, DomainSubscription, PaymentHistory
from content.models import Domain, Course
from datetime import datetime, timezone as dt_timezone
from .serializers import DomainSubscriptionSerializer
from rest_framework import viewsets

stripe.api_key = settings.STRIPE_SECRET_KEY


class FreeTierActivateView(APIView):
    """
    Activates one-time free tier for a user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        domain_id = request.data.get('domain_id')
        course_id = request.data.get('course_id')

        # Check if user already consumed free tier
        existing = FreeTierActivation.objects.filter(user=request.user).first()
        if existing:
            return Response({'error': 'Free tier already used or active.'}, status=400)

        domain = get_object_or_404(Domain, id=domain_id)
        course = get_object_or_404(Course, id=course_id)

        FreeTierActivation.objects.create(
            user=request.user,
            domain=domain,
            course=course,
            is_active=True,
            has_consumed=True
        )
        return Response({'message': 'Free tier activated successfully.'}, status=200)


class CreateCheckoutSessionView(APIView):
    """
    Creates a Stripe Checkout session for subscription.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        domain_id = request.data.get('domain_id')
        plan_interval = request.data.get('plan_interval')  # monthly or yearly
        price_id = request.data.get('price_id')  # should come from frontend for selected domain

        domain = get_object_or_404(Domain, id=domain_id)

        # Create Stripe customer (or reuse existing)
        customer = stripe.Customer.create(
            email=request.user.email,
            metadata={'user_id': request.user.id}
        )

        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=settings.FRONTEND_SUCCESS_URL,
            cancel_url=settings.FRONTEND_CANCEL_URL,
            metadata={'user_id': request.user.id, 'domain_id': domain.id}
        )

        return Response({'sessionId': checkout_session.id, 'checkout_url': checkout_session.url})


import logging

logger = logging.getLogger(__name__)

class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        # Verify Stripe webhook
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return Response(status=400)

        try:
            event_type = event.get('type')
            data_object = event.get('data', {}).get('object', {})

            # --- Checkout Session Completed ---

            if event_type == 'checkout.session.completed':
                session = data_object
                logger.info(f"Processing checkout.session.completed: {session}")

                subscription_id = session.get('subscription')
                user_id = int(session.get('metadata', {}).get('user_id', 0))
                domain_id = int(session.get('metadata', {}).get('domain_id', 0))

                if subscription_id and user_id and domain_id:
                    subscription = stripe.Subscription.retrieve(subscription_id)

                    DomainSubscription.objects.update_or_create(
                        user_id=user_id,
                        domain_id=domain_id,
                        defaults={
                            'stripe_customer_id': session.get('customer'),
                            'stripe_subscription_id': subscription.id,
                            'price_id': subscription['items']['data'][0]['price']['id'] if subscription.get('items') else None,
                            'plan_interval': subscription['items']['data'][0]['price']['recurring']['interval'] if subscription.get('items') else None,
                            'status': subscription.get('status', 'incomplete'),
                            'current_period_start': datetime.fromtimestamp(
                                subscription.get('current_period_start', datetime.now().timestamp()), tz=dt_timezone.utc
                            ),
                            'current_period_end': datetime.fromtimestamp(
                                subscription.get('current_period_end', datetime.now().timestamp()), tz=dt_timezone.utc
                            ),
                            'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
                            'is_active': True,
                        }
                    )

                    # Deactivate free tier if active
                    FreeTierActivation.objects.filter(user_id=user_id, is_active=True).update(is_active=False)
                else:
                    logger.warning("checkout.session.completed missing subscription, user_id, or domain_id")

            # --- Invoice Payment Succeeded ---
            elif event_type == 'invoice.payment_succeeded':
                invoice = data_object
                subscription_id = invoice.get('subscription')

                if subscription_id:
                    sub = DomainSubscription.objects.filter(stripe_subscription_id=subscription_id).first()
                    if sub:
                        subscription = stripe.Subscription.retrieve(subscription_id)
                        sub.current_period_end = datetime.fromtimestamp(
                            subscription.get('current_period_end', datetime.now().timestamp()), tz=dt_timezone.utc
                        )
                        sub.status = 'active'
                        sub.save()

                        PaymentHistory.objects.create(
                            domain_subscription=sub,
                            stripe_invoice_id=invoice.get('id'),
                            amount=invoice.get('amount_paid', 0) / 100,
                            currency=invoice.get('currency', 'usd'),
                            paid_at=datetime.now(dt_timezone.utc),
                            status='paid'
                        )
                    else:
                        logger.warning(f"No DomainSubscription found for subscription_id {subscription_id}")
                else:
                    logger.warning("invoice.payment_succeeded event without subscription_id")


            # --- Subscription Deleted ---
            elif event_type == 'customer.subscription.deleted':
                sub_id = data_object.get('id')
                if sub_id:
                    DomainSubscription.objects.filter(stripe_subscription_id=sub_id).update(
                        status='canceled', is_active=False
                    )
                else:
                    logger.warning("customer.subscription.deleted event missing id")

            else:
                logger.info(f"Unhandled Stripe event type: {event_type}")

        except Exception as e:
            logger.exception(f"Error processing Stripe event {event.get('type')}: {e}")
            return Response(status=500)

        return Response(status=200)


class CancelSubscriptionView(APIView):
    """
    Cancels a user's active subscription at period end.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, domain_id):
        sub = get_object_or_404(DomainSubscription, user=request.user, domain_id=domain_id, is_active=True)
        stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
        sub.cancel_at_period_end = True
        sub.save()
        return Response({'message': 'Subscription will cancel at period end.'}, status=200)


class SubscriptionStatusView(APIView):
    """
    Returns the user's subscription status for a given domain.
    Possible statuses:
    - 'none'          → no subscription exists
    - 'active'        → user has an active paid subscription
    - 'past_due'      → payment failed, subscription past due
    - 'canceled'      → canceled but may still be active until period end
    - 'incomplete'    → checkout not finished
    - 'incomplete_expired' → incomplete and expired
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, domain_id):
        sub = DomainSubscription.objects.filter(user=request.user, domain_id=domain_id).first()

        if not sub:
            return Response({
                'status': 'none',
                'is_active': False,
                'domain_id': domain_id,
                'plan_interval': None,
                'cancel_at_period_end': None,
                'current_period_start': None,
                'current_period_end': None,
            })

        data = {
            'status': sub.status,
            'is_active': sub.is_active,
            'domain_id': sub.domain.id,
            'plan_interval': sub.plan_interval,
            'cancel_at_period_end': sub.cancel_at_period_end,
            'current_period_start': sub.current_period_start,
            'current_period_end': sub.current_period_end,
        }
        return Response(data)


class FreeTierStatusView(APIView):
    """
    Returns the user's free tier status:
    - 'not_activated': user never activated
    - 'active': user currently has an active free tier
    - 'expired': user used the free tier before but it’s no longer active
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        activation = FreeTierActivation.objects.filter(user=request.user).first()

        if not activation:
            # Never activated
            status_text = 'not_activated'
        elif activation.is_active:
            # Currently active
            status_text = 'active'
        else:
            # Used before and now expired forever
            status_text = 'expired'

        data = {
            'status': status_text,
            'domain_id': activation.domain.id if activation else None,
            'course_id': activation.course.id if activation else None,
            'activated_at': activation.activated_at if activation else None,
        }
        return Response(data)


class UserDomainSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns all DomainSubscription records for the authenticated user.
    """
    serializer_class = DomainSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return the active subscriptions belonging to the logged-in user
        return DomainSubscription.objects.filter(user=self.request.user, is_active=True)