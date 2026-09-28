from uuid import uuid4

from django.conf import settings
from django.db.models import F
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class UserAccountManager(BaseUserManager):
    def create_superuser(self, username, email, password, **other_fields):
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        user = self.create_user(
            slug=slugify(username),
            full_name=username,
            email=email,
            password=password,
            **other_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_user(self, username, email, password=None, **other_fields):
        if not email:
            raise ValueError("Email address is required!")

        email = self.normalize_email(email)
        if password is not None:
            user = self.model(
                slug=username,
                email=email,
                password=password,
                **other_fields
            )
            user.save()
        else:
            user = self.model(
                slug=username,
                email=email,
                password=password,
                **other_fields
            )
            user.set_unusable_password()
            user.save()

        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_ADMIN = "admin"
    ROLES = (
        (ROLE_ADMIN, ROLE_ADMIN),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    slug = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=128, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    company = models.TextField(null=True, blank=True)
    position = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=128, null=True, blank=True)
    country = models.CharField(max_length=128, null=True, blank=True)
    contact = models.CharField(max_length=256, null=True, blank=True)
    hat = models.JSONField(null=True, blank=True)
    rating = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)

    membership_started_at = models.DateTimeField(null=True, blank=True)
    membership_expires_at = models.DateTimeField(null=True, blank=True)
    telegram_data = models.JSONField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    profile_cache = models.JSONField(default=dict, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    telegram_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    roles = ArrayField(models.CharField(max_length=32, choices=ROLES), default=list, null=False)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    objects = UserAccountManager()

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

    def increment_vote_count(self):
        User.objects.filter(pk=self.pk).update(upvotes=F("upvotes") + 1)
        self.upvotes += 1

    @property
    def is_admin(self):
        return self.ROLE_ADMIN in self.roles
