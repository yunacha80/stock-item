from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import now
from django.db.models.signals import post_save
# from .models import Category

# Create your models here.


class User(AbstractUser):
    first_name = None
    last_name = None
    date_joined = None
    username = None
    groups = None
    user_permissions = None


    name = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    USERNAME_FIELD = "name"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]


    class Meta:
        db_table = "users"



def validate_ItemCategory_limit(user):
    """カテゴリは最大10個まで登録可能です。"""
    if ItemCategory.objects.filter(user=user).count() >= 10:
        raise ValidationError("カテゴリは最大10個まで登録可能です。")

class ItemCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, blank=False, null=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # def clean(self):
    #     """カテゴリ数の制限をチェック"""
    #     if not self.user:
    #         return
    #     validate_ItemCategory_limit(self.user)

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
        
class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
        return self.name
    
    @property
    def needs_restock(self):
        """在庫数が最低在庫数を下回っているか確認"""
        return self.stock_quantity < self.stock_min_threshold
    
    def update_stock(self, purchased_quantity):
        self.stock_quantity += purchased_quantity
        self.save()


    

class StoreItemReference(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    price = models.IntegerField(null=True, blank=True)
    price_per_unit = models.FloatField(null=True, blank=True)
    memo = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.store.name} - {self.item.name}"





 
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
    purchased_date = models.DateField()
    purchased_quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name} - {self.purchased_date} - 数量: {self.purchased_quantity}"
    


class PurchaseItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    planned_purchase_quantity = models.IntegerField(default=0)
    purchased_quantity = models.IntegerField(null=True, blank=True)
    purchased_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_stock_and_check(self):
        """在庫を更新し、リストから削除するかチェック"""
        if self.purchased_quantity:
            self.item.update_stock(self.purchased_quantity)
            if self.item.stock_quantity >= self.item.stock_min_threshold:
                self.delete()

    
