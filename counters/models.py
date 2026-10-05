from django.conf import settings
from django.db import models


class Rating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ratings",
        on_delete=models.CASCADE,
    )
    change = models.IntegerField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ratings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="ratings_user_created_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.change:+d} {self.reason}"
