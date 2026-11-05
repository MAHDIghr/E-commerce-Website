"""Agrégats internes uniquement : aucun traceur, événement navigateur ou identifiant exporté."""
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Min, Q, Sum
from django.utils import timezone
from .models import Order, PaymentAttempt, ReturnRequest, Refund


def report(start, end):
    if timezone.is_naive(start) or timezone.is_naive(end) or start >= end:
        raise ValueError('Fournir une période croissante avec fuseaux horaires explicites.')
    cohort = Order.objects.annotate(confirmed=Min('lifecycle_events__created_at', filter=Q(
        lifecycle_events__event_type='payment_confirmed', lifecycle_events__source='stripe'))).filter(confirmed__gte=start, confirmed__lt=end)
    result = []
    for currency in cohort.values_list('currency', flat=True).distinct().order_by('currency'):
        orders = cohort.filter(currency=currency)
        # La sous-requête élimine les doublons d'événement, sans agréger les montants sur une jointure.
        selected = Order.objects.filter(pk__in=orders.values('pk'))
        count = selected.count()
        gross = selected.aggregate(value=Sum('total'))['value'] or Decimal('0.00')
        requests = ReturnRequest.objects.filter(order__in=selected).values('order_id').distinct().count()
        refunded = Refund.objects.filter(order__in=selected, currency=currency, status=Refund.SUCCEEDED,
                                        confirmed_at__lt=end).aggregate(value=Sum('amount'))['value'] or Decimal('0.00')
        result.append({'currency':currency, 'purchases':count, 'gross_order_value':str(gross.quantize(Decimal('0.01'))),
                       'average_order_value':str((gross / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if count else None,
                       'orders_with_return_request_observed_now':requests,
                       'return_request_share_observed_now':str(Decimal(requests) / count) if count else None,
                       'confirmed_refunds_before_period_end':str(refunded.quantize(Decimal('0.01')))})
    attempts = PaymentAttempt.objects.filter(created_at__gte=start, created_at__lt=end)
    return {'start_inclusive':start.isoformat(), 'end_exclusive':end.isoformat(), 'observed_at':timezone.now().isoformat(),
            'source':'internal_existing_order_records', 'currencies':result,
            'payment_attempt_records':attempts.count(),
            'failed_payment_attempt_records':attempts.filter(status=PaymentAttempt.FAILED).count(),
            'visitor_conversion':None, 'device_conversion':None, 'cart_to_checkout':None,
            'step_abandonment':None, 'unavailable_reason':'Aucun suivi de visiteurs ou événement navigateur activé.'}
