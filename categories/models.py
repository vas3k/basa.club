from django.db import models


class Category(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    root = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="descendants",
    )
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
