import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from checkout.conversion import report

class Command(BaseCommand):
    help = 'Agrégats internes sans contacts ; période ISO avec fuseau, début inclus / fin exclue.'
    def add_arguments(self, parser):
        parser.add_argument('--start', required=True)
        parser.add_argument('--end', required=True)
    def handle(self, *args, **options):
        try:
            start, end = parse_datetime(options['start']), parse_datetime(options['end'])
        except ValueError as exc:
            raise CommandError('Dates ISO valides requises.') from exc
        if start is None or end is None:
            raise CommandError('Dates ISO avec fuseau requises.')
        try:
            data = report(start,end)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(data,ensure_ascii=False,indent=2))
