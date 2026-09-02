from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import AppFile
from .storage import delete_storage_key


@receiver(post_delete, sender=AppFile)
def remove_managed_file_bytes(sender, instance, **kwargs):
    if instance.storage_key:
        delete_storage_key(instance.storage_key)
