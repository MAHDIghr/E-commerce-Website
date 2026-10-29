import uuid
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .models import Order, OrderNotification


class ProcessOrderNotificationsCommandTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(),
            email="guest@example.test",
            full_name="Client invité",
            address_line1="1 rue du Test",
            postal_code="75001",
            city="Paris",
            shipping_method="standard",
            subtotal=Decimal("30.00"),
            total=Decimal("30.00"),
        )

    def make_notification(self, *, status=OrderNotification.PENDING, attempts=0):
        return OrderNotification.objects.create(
            order=self.order,
            event_key=f"test-{uuid.uuid4()}",
            recipient=self.order.email,
            status=status,
            attempts=attempts,
            payload={"subject": "Test", "message": "Test"},
        )

    def test_dry_run_does_not_change_pending_notification(self):
        notification = self.make_notification()
        call_command("process_order_notifications", "--dry-run")
        notification.refresh_from_db()
        self.assertEqual(notification.status, OrderNotification.PENDING)
        self.assertEqual(notification.attempts, 0)

    @patch("checkout.management.commands.process_order_notifications.deliver_notification")
    def test_processes_pending_notifications(self, deliver):
        notification = self.make_notification()
        deliver.return_value = notification
        call_command("process_order_notifications")
        deliver.assert_called_once_with(notification.pk)

    def test_rejects_unsafe_batch_limits(self):
        with self.assertRaises(CommandError):
            call_command("process_order_notifications", "--limit", "1000")

    def test_recovers_stale_sending_notification(self):
        notification = self.make_notification(status=OrderNotification.SENDING, attempts=1)
        OrderNotification.objects.filter(pk=notification.pk).update(
            updated_at=timezone.now() - timezone.timedelta(minutes=30)
        )
        with patch("checkout.management.commands.process_order_notifications.deliver_notification") as deliver:
            deliver.return_value = notification
            call_command("process_order_notifications", "--stale-minutes", "15")
            notification.refresh_from_db()
            self.assertEqual(notification.status, OrderNotification.FAILED)
            deliver.assert_called_once_with(notification.pk)
