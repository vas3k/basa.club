from django.db import models


class GeoCountry(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    items_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geo_countries"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class GeoCity(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=255, blank=True, default="")
    country = models.ForeignKey(GeoCountry, on_delete=models.CASCADE, related_name="cities")
    sort_order = models.PositiveIntegerField(default=0)
    items_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geo_cities"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
