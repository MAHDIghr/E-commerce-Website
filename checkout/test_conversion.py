import json
from io import StringIO
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.management import call_command
from django.core.management.base import CommandError
from . import test_order_tracking as fixtures
from .models import OrderEvent
from .conversion import report

class ConversionTests(TestCase):
    setUp = fixtures.PublicOrderTrackingTests.setUp
    def test_payment_confirmation_deduplicates_and_never_exports_contacts_or_reference(self):
        for _ in range(2):
            OrderEvent.objects.create(order=self.order,event_type='payment_confirmed',source='stripe')
        now=timezone.now()
        result=report(now-timedelta(days=1),now+timedelta(seconds=1))
        self.assertEqual(result['currencies'][0]['purchases'],1)
        self.assertEqual(result['currencies'][0]['gross_order_value'],'24.90')
        serialized=json.dumps(result)
        for secret in [self.order.email,self.order.full_name,str(self.order.public_id),self.order.address_line1]:
            self.assertNotIn(secret,serialized)
    def test_paid_status_or_click_without_payment_proof_is_not_purchase(self):
        now=timezone.now()
        self.assertEqual(report(now-timedelta(days=1),now)['currencies'],[])
    def test_period_requires_timezone_and_command_outputs_aggregates(self):
        with self.assertRaises(CommandError):
            call_command('conversion_report',start='2026-01-01T00:00:00',end='2026-02-01T00:00:00',stdout=StringIO())
        output=StringIO()
        call_command('conversion_report',start='2026-01-01T00:00:00Z',end='2026-02-01T00:00:00Z',stdout=output)
        self.assertIsNone(json.loads(output.getvalue())['visitor_conversion'])
