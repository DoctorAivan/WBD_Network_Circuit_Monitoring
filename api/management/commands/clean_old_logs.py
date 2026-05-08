from django.core.management.base import BaseCommand
from api.models import ServerLog

class Command(BaseCommand):
    help = 'Limpia la base de datos manteniendo solo los registros del año 2026'

    def handle(self, *args, **options):
        deleted_count, _ = ServerLog.objects.exclude(timestamp__year=2026).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Limpieza completada. Se eliminaron {deleted_count} registros.')
        )
