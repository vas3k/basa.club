from django.core.management.base import BaseCommand
from django.utils import timezone

from authn.models import Code


class Command(BaseCommand):
    help = "Delete login codes whose expiration time has passed."

    def handle(self, *args, **options):
        deleted, _ = Code.objects.filter(
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired auth codes"))
