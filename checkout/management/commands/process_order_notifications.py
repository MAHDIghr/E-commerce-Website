"""Traite la file persistante des notifications de commande.

À exécuter périodiquement par un ordonnanceur externe. La commande ne configure
pas elle-même de tâche système et ne doit pas être lancée en concurrence sans
limite : les notifications sont verrouillées au moment de leur envoi.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from checkout.lifecycle import deliver_notification
from checkout.models import OrderNotification


class Command(BaseCommand):
    help = "Traite les notifications de commande en attente ou en échec."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--stale-minutes", type=int, default=15)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        stale_minutes = options["stale_minutes"]
        if limit < 1 or limit > 500:
            raise CommandError("--limit doit être compris entre 1 et 500.")
        if stale_minutes < 5 or stale_minutes > 1440:
            raise CommandError("--stale-minutes doit être compris entre 5 et 1440.")

        stale_before = timezone.now() - timedelta(minutes=stale_minutes)
        stale_query = OrderNotification.objects.filter(
            status=OrderNotification.SENDING,
            updated_at__lt=stale_before,
        )
        stale_count = stale_query.count()
        if not options["dry_run"] and stale_count:
            stale_query.update(
                status=OrderNotification.FAILED,
                error_message="Tentative interrompue avant confirmation finale ; reprise contrôlée.",
                updated_at=timezone.now(),
            )

        queue = OrderNotification.objects.filter(
            status__in=[OrderNotification.PENDING, OrderNotification.FAILED],
            attempts__lt=5,
        ).order_by("created_at", "pk")[:limit]
        ids = list(queue.values_list("pk", flat=True))
        if options["dry_run"]:
            self.stdout.write(
                f"Simulation : {len(ids)} notification(s) prête(s), {stale_count} tentative(s) bloquée(s)."
            )
            return

        sent = failed = skipped = 0
        for notification_id in ids:
            result = deliver_notification(notification_id)
            if result.status == OrderNotification.SENT:
                sent += 1
            elif result.status == OrderNotification.FAILED:
                failed += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Traitement terminé : {sent} envoyée(s), {failed} en échec, "
            f"{skipped} inchangée(s), {stale_count} tentative(s) bloquée(s) récupérée(s)."
        ))
