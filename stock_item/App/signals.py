from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Item, Store, StoreItemReference

@receiver(post_save, sender=Item)
def create_store_item_references_for_new_item(sender, instance, created, **kwargs):
    if created:
        stores = Store.objects.all()
        for store in stores:
            StoreItemReference.objects.get_or_create(store=store, item=instance)

@receiver(post_save, sender=Store)
def create_store_item_references_for_new_store(sender, instance, created, **kwargs):
    if created:
        items = Item.objects.all()
        for item in items:
            StoreItemReference.objects.get_or_create(store=instance, item=item)
