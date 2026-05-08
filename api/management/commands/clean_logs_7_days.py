from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import ServerLog

class Command(BaseCommand):
    help = 'Elimina todos los registros con una antigüedad mayor a 7 días'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=7)
        deleted_count, _ = ServerLog.objects.filter(timestamp__lt=cutoff_date).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Limpieza completada. Se eliminaron {deleted_count} registros más antiguos a 7 días.')
        )
