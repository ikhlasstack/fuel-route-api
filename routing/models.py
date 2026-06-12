from django.db import models


class FuelStation(models.Model):
    opis_id = models.CharField(max_length=32, blank=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=8)
    rack_id = models.CharField(max_length=32, blank=True)
    retail_price = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["state"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.retail_price})"
