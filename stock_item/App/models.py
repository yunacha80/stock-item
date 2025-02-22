from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import now
from django.db.models.signals import post_save
from datetime import timedelta

# from .models import Category

# Create your models here.


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None):
        user = self.create_user(email, name, password)
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    name = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=200)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"



class ItemCategory(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, blank=False, null=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "App_category"

    

class Store(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, blank=False, null=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    travel_time_home_min = models.IntegerField(null=False, blank=False, default=0, verbose_name="自宅からの移動時間（分）")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItemManager(models.Manager):
    def update_stock(self, item, purchased_quantity):
        """
        在庫を更新し、必要に応じて買い物リストに追加。
        """
        from .models import PurchaseItem  # 遅延インポートを推奨

        item.stock_quantity += purchased_quantity
        item.save()

        if item.stock_quantity < item.stock_min_threshold:
            planned_purchase_quantity = max(item.stock_min_threshold - item.stock_quantity, 0)
            PurchaseItem.objects.get_or_create(
                item=item,
                defaults={'planned_purchase_quantity': planned_purchase_quantity}
            )

class Item(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    category = models.ForeignKey('ItemCategory', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    stock_quantity = models.IntegerField(default=0)
    memo = models.CharField(max_length=100, blank=True, null=True)
    stock_min_threshold = models.IntegerField(default=1)
    purchase_interval_days = models.IntegerField(null=True, blank=True, verbose_name="購入頻度（日）")
    reminder = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - 在庫最低値: {self.stock_min_threshold}"

    def update_purchase_frequency(self):
        """
        購入履歴を基に購入頻度を計算し、purchase_interval_days を更新します。
        """
        from .models import PurchaseHistory

        histories = PurchaseHistory.objects.filter(item=self).order_by("purchased_date")
        if histories.count() > 1:
            intervals = [
                (histories[i].purchased_date - histories[i - 1].purchased_date).days
                for i in range(1, histories.count())
            ]
            self.purchase_interval_days = sum(intervals) // len(intervals)
            self.save()

    def needs_restock(self):
        """
        在庫が最低値を下回っているかを確認します。
        """
        return self.stock_quantity < self.stock_min_threshold
    
    def update_stock(self, purchased_quantity):
        """
        在庫を更新し、最低在庫数を下回った場合に買い物リストに追加または更新。
        """
        # 在庫を更新
        self.stock_quantity += purchased_quantity
        self.save()

    # 在庫が最低在庫数を下回った場合の処理
        
        if self.needs_restock():
            planned_purchase_quantity = self.stock_min_threshold - self.stock_quantity
            purchase_item, created = PurchaseItem.objects.get_or_create(
                item=self,
                defaults={"planned_purchase_quantity": planned_purchase_quantity}
            )
            if not created:
                # 既存の買い物リストアイテムを更新
                purchase_item.planned_purchase_quantity = planned_purchase_quantity
                purchase_item.save()

                
    def calculate_next_due_date(self):
        """
        購入頻度に基づき次回購入予定日を計算。
        """
        if self.purchase_interval_days:
            last_purchase = PurchaseHistory.objects.filter(item=self).order_by("-purchased_date").first()
            if last_purchase:
                return last_purchase.purchased_date + timedelta(days=self.purchase_interval_days)
        return None

    def check_reminder_due(self):
        """
        リマインダーを送るべきかどうかを判定。
        """
        if not self.reminder:
            return False
        next_due_date = self.calculate_next_due_date()
        if next_due_date and next_due_date <= now().date():
            return True
        return False

    def update_stock_and_manage_list(self, purchased_quantity):
        """
        在庫を更新し、必要に応じて買い物リストから削除。
        """
        # 在庫を更新
        self.stock_quantity += purchased_quantity
        self.save()

        # 在庫が最低在庫数を上回った場合の処理
        if self.stock_quantity >= self.stock_min_threshold:
            PurchaseItem.objects.filter(item=self).delete()

        # 購入履歴の保存
        PurchaseHistory.objects.create(
            item=self,
            purchased_quantity=purchased_quantity,
            purchased_date=now().date()
        )

    



class StoreItemReference(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    price = models.IntegerField(null=True, blank=True, verbose_name="価格")
    price_per_unit = models.IntegerField(null=True, blank=True, verbose_name="単位数")
    price_unknown = models.BooleanField(default=False, verbose_name="価格不明")  
    no_price = models.BooleanField(default=False, verbose_name="取り扱いなし")
    memo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.store.name} - {self.item.name}"

    def clean(self):
        """
        バリデーションロジック:
        - price と price_per_unit が指定された場合、正の値であることを確認。
        """
        if self.price is not None and self.price <= 0:
            raise ValidationError("価格は正の値である必要があります。")
        if self.price_per_unit is not None and self.price_per_unit <= 0:
            raise ValidationError("単位数は正の値である必要があります。")
        
    




 
# 店舗間移動時間
class StoreTravelTime(models.Model):
    store1 = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store1_travel_times')
    store2 = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store2_travel_times')
    travel_time_min = models.IntegerField(verbose_name="移動時間（分）")  # 移動時間（分）

    def __str__(self):
        return f"{self.store1.name} to {self.store2.name} : {self.travel_time_min}分"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['store1', 'store2'], name='unique_store_travel_time')
        ]
    


    
# # 購入履歴
# class PurchaseHistory(models.Model):
#       item = models.ForeignKey('Item', related_name='purchase_histories', on_delete=models.CASCADE)
#       purchased_date = models.DateField()
#       purchased_quantity = models.IntegerField()
#       created_at = models.DateTimeField(auto_now_add=True)
#       updated_at = models.DateTimeField(auto_now=True)

#       def __str__(self):
#         return f"{self.item.name} - {self.purchased_date} - 数量: {self.purchased_quantity}"
      



class PurchaseHistory(models.Model):
    item = models.ForeignKey(Item, related_name='purchase_histories', on_delete=models.CASCADE)
    purchased_date = models.DateField(null=True, blank=True)
    purchased_quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name} - {self.purchased_date} - 数量: {self.purchased_quantity}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 購入頻度を更新
        self.item.update_purchase_frequency()
    


class PurchaseItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="purchase_items")
    planned_purchase_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchase_items"

    def __str__(self):
        return f"{self.item.name} - 購入予定数: {self.planned_purchase_quantity}"

    
