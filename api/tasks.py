from django.utils import timezone
from datetime import timedelta
from api.models import ServerLog

def clean_old_server_logs():
    cutoff_date = timezone.now() - timedelta(days=7)
    deleted_count, _ = ServerLog.objects.filter(created__lt=cutoff_date).delete()
    return deleted_count