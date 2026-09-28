from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from users.models import User
from utils.strings import random_code
from vas3k_base.exceptions import RateLimitException


class Code(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    recipient = models.CharField(max_length=128, db_index=True)
    code = models.CharField(max_length=128, db_index=True)
    user = models.ForeignKey(User, related_name="auth_codes", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)
    ipaddress = models.GenericIPAddressField(null=True, db_index=True)
    useragent = models.CharField(max_length=512, null=True, blank=True)
    telegram_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "auth_codes"
        ordering = ["-created_at"]

    @classmethod
    def create_for_user(cls, user, recipient, length=None, ipaddress=None, useragent=None):
        recipient = (recipient or "").lower()
        now = timezone.now()
        window = now - settings.AUTH_MAX_CODE_TIMEDELTA
        last_codes_count = cls.objects.filter(recipient=recipient, created_at__gte=window).count()
        if last_codes_count >= settings.AUTH_MAX_CODE_COUNT:
            raise RateLimitException(title="Вы запросили слишком много кодов", message="Подождите немного")

        if ipaddress:
            last_codes_from_ip_count = cls.objects.filter(ipaddress=ipaddress, created_at__gte=window).count()
            if last_codes_from_ip_count >= settings.AUTH_MAX_CODE_COUNT_PER_IP:
                raise RateLimitException(title="Вы запросили слишком много кодов", message="Подождите немного")

        last_codes_total_count = cls.objects.filter(created_at__gte=window).count()
        if last_codes_total_count >= settings.AUTH_MAX_CODE_COUNT_TOTAL:
            raise RateLimitException(title="Вы запросили слишком много кодов", message="Подождите немного")

        return cls.objects.create(
            recipient=recipient,
            user=user,
            code=random_code(length or settings.AUTH_CODE_LENGTH),
            expires_at=now + settings.AUTH_CODE_EXPIRATION_TIMEDELTA,
            ipaddress=ipaddress,
            useragent=useragent,
        )

    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())
