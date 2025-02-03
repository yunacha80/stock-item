from django.core.management.base import BaseCommand
from App.models import Item, Store, StoreItemReference

class Command(BaseCommand):
    help = "全てのアイテムと店舗を紐付けする StoreItemReference を作成します"

    def handle(self, *args, **kwargs):
        stores = Store.objects.all()
        items = Item.objects.all()

        for store in stores:
            for item in items:
                StoreItemReference.objects.get_or_create(store=store, item=item)

        self.stdout.write(self.style.SUCCESS("StoreItemReference の初期化が完了しました"))
