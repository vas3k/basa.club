from uuid import uuid4

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from django.utils import timezone

from common.models import SoftDeleteMixin, SoftDeleteQuerySet


class UserAccountManager(BaseUserManager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def create_superuser(self, email, password=None, **other_fields):
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        if other_fields["is_staff"] is not True or other_fields["is_superuser"] is not True:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True")
        return self.create_user(email=email, password=password, **other_fields)

    def create_user(self, username=None, email=None, password=None, **other_fields):
        if not email:
            raise ValueError("Email address is required!")
        slug = other_fields.pop("slug", None) or username
        if not slug:
            raise ValueError("A slug is required!")
        user = self.model(slug=slug, email=self.normalize_email(email), **other_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(SoftDeleteMixin, AbstractBaseUser, PermissionsMixin):
    ROLE_GOD = "god"
    ROLE_MODERATOR = "moderator"
    ROLES = (
        (ROLE_GOD, "Бог"),
        (ROLE_MODERATOR, "Модератор"),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    slug = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=128, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    club_slug = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=128, null=True, blank=True)
    country = models.CharField(max_length=128, null=True, blank=True)
    contact = models.CharField(max_length=256, null=True, blank=True)
    hat = models.JSONField(null=True, blank=True)
    rating = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)
    items_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)

    membership_started_at = models.DateTimeField(null=True, blank=True)
    membership_expires_at = models.DateTimeField(null=True, blank=True)
    telegram_data = models.JSONField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    telegram_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    roles = ArrayField(models.CharField(max_length=32, choices=ROLES), default=list, null=False)
    is_banned_until = models.DateTimeField(null=True, blank=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserAccountManager()
    all_objects = models.Manager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["slug"]

    class Meta:
        db_table = "users"

    def get_absolute_url(self):
        return reverse("user_profile", args=[self.slug])

    def default_avatar(self):
        if self.avatar:
            return self.avatar
        return settings.DEFAULT_AVATAR

    @property
    def is_god(self):
        return self.is_superuser

    @property
    def is_moderator(self):
        return self.is_staff or self.is_superuser

    @property
    def is_banned(self):
        if self.is_superuser:
            return False
        return bool(self.is_banned_until and self.is_banned_until > timezone.now())

    @property
    def is_permanently_banned(self):
        return self.is_banned and (self.is_banned_until - timezone.now()).days > 365 * 1000

    @property
    def is_active_membership(self):
        now = timezone.now()
        if not self.membership_expires_at or self.membership_expires_at < now:
            return False
        if self.membership_started_at and self.membership_started_at > now:
            return False
        return True

    def get_metadata_value(self, key, default=None):
        return (self.metadata or {}).get(key, default)

    def set_metadata_value(self, key, value):
        metadata = dict(self.metadata or {})
        metadata[key] = value
        self.metadata = metadata
