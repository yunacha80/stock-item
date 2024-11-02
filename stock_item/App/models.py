from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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



def validate_category_limit(value):
    if len(value) > 10:
        raise ValidationError('カテゴリは最大10個まで登録可能です。')


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=0) 

    def __str__(self):
        return self.name
    
class Store(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        
class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=50)
    stock_quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)  # 価格
    unit_quantity = models.IntegerField(null=True, blank=True)  # 入数
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    memo = models.CharField(max_length=100, blank=True)
    stock_min_threshold = models.IntegerField(default=0)
    reminder = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class StoreItemReference(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 価格
    unit_quantity = models.IntegerField(null=True, blank=True)  # 入数
    memo = models.CharField(max_length=100, blank=True)  # 価格のメモ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def unit_price(self):
        return self.price / self.unit_quantity if self.unit_quantity else None

    def __str__(self):
        return f"{self.item.name} - {self.store.name}"
    