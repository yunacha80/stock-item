from django.test import TestCase
from App.models import User, Store, Item, ItemCategory, StoreItemReference, StoreTravelTime, PurchaseItem
from App.views import calculate_route

class CalculateRouteTestCase(TestCase):
    def setUp(self):
        # ユーザー作成
        self.user = User.objects.create_user(
            name='テストユーザー',
            email='test@example.com',
            password='password'
        )
        # 店舗作成
        self.store1 = Store.objects.create(user=self.user, name='Store A', travel_time_home_min=10)
        self.store2 = Store.objects.create(user=self.user, name='Store B', travel_time_home_min=5)
        self.store3 = Store.objects.create(user=self.user, name='Store C', travel_time_home_min=15)

        # 店舗間の移動時間
        StoreTravelTime.objects.create(store1=self.store1, store2=self.store2, travel_time_min=5)
        StoreTravelTime.objects.create(store1=self.store2, store2=self.store1, travel_time_min=5)
        StoreTravelTime.objects.create(store1=self.store1, store2=self.store3, travel_time_min=10)
        StoreTravelTime.objects.create(store1=self.store3, store2=self.store1, travel_time_min=10)
        StoreTravelTime.objects.create(store1=self.store2, store2=self.store3, travel_time_min=8)
        StoreTravelTime.objects.create(store1=self.store3, store2=self.store2, travel_time_min=8)

        # 商品作成
        self.category = ItemCategory.objects.create(user=self.user, name='テストカテゴリ', display_order=1)
        self.item1 = Item.objects.create(
            user=self.user,
            name='Item 1',
            category=self.category,
            stock_quantity=0,
            stock_min_threshold=1
            )
        self.item2 = Item.objects.create(user=self.user, name='Item 2', stock_quantity=0, stock_min_threshold=1,category=self.category)

        # 商品と店舗の関連（StoreItemReference）
        StoreItemReference.objects.update_or_create(
               store=self.store1,
               item=self.item1,
               defaults={"price": 100, "price_per_unit": 1}
            )
        
        StoreItemReference.objects.update_or_create(
            store=self.store2,
            item=self.item1,
            defaults={"price": 90, "price_per_unit": 1}
        )
        StoreItemReference.objects.update_or_create(
            store=self.store2,
            item=self.item2,
            defaults={"price": 80, "price_per_unit": 1}
        )
        StoreItemReference.objects.update_or_create(
            store=self.store3,       
            item=self.item2,
            defaults={"price": 70, "price_per_unit": 1}
        )
        # 購入予定アイテム
        self.purchase_item1 = PurchaseItem.objects.create(item=self.item1, planned_purchase_quantity=1)
        self.purchase_item2 = PurchaseItem.objects.create(item=self.item2, planned_purchase_quantity=1)

    def test_strategy_price(self):
        result = calculate_route([self.purchase_item1, self.purchase_item2], 'price', user=self.user)
        self.assertEqual(result['details']['Item 1']['store'], 'Store B')
        self.assertEqual(result['details']['Item 2']['store'], 'Store C')

    def test_strategy_time(self):
        result = calculate_route([self.purchase_item1, self.purchase_item2], 'time', user=self.user)
        self.assertIn(result['route'][0].name, ['Store B', 'Store C'])
        self.assertGreaterEqual(result['total_time'], 10)  # 最短の往復は10分以上

    def test_strategy_balance(self):
        result = calculate_route([self.purchase_item1, self.purchase_item2], 'balance', user=self.user)
        self.assertTrue('Item 1' in result['details'])
        self.assertTrue('Item 2' in result['details'])
