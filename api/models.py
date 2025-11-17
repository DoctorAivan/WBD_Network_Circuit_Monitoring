from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=256, blank=True, null=True)
    color = models.CharField(max_length=7)

    def __str__(self):
        return self.name


class Circuit(models.Model):
    target_host = models.CharField(max_length=100, unique=True, db_index=True)
    range_up = models.FloatField(default=0)
    range_down = models.FloatField(default=0)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="circuits")
    description = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return self.target_host


class ServerLog(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    source_host = models.CharField(max_length=100, db_index=True)
    circuit = models.ForeignKey(Circuit, on_delete=models.CASCADE, related_name="logs")
    min_value = models.FloatField()
    avg_value = models.FloatField()
    max_value = models.FloatField()
    stddev_value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["timestamp", "source_host", "circuit"],
                name="unique_log_entry"
            ),
        ]
        indexes = [
            models.Index(fields=["timestamp", "source_host", "circuit"]),
        ]
        ordering = ["-timestamp"]
        verbose_name = "Server Log"
        verbose_name_plural = "Server Logs"

    def __str__(self):
        return f"{self.timestamp} | {self.source_host} -> {self.circuit.target_host}"
