from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from App.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import inlineformset_factory,modelformset_factory
from .models import Item,StoreItemReference, Category,PurchaseHistory,Store,StoreTravelTime



class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["name", "email", "password1","password2"]
    def clean_email(self):
        email =self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")
        return email 
    

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()

    def clean(self):
        print("ログインフォームのクリーンが呼び出された")
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        print(email, password)
        self.user = authenticate(email=email, password=password)
        if self.user is None:
            raise forms.ValidationError("認証に失敗しました")
        return self.cleaned_data
    
class CustomPasswordChangeForm(PasswordChangeForm):
    pass

class EmailChangeForm(forms.Form):
     current_email = forms.EmailField(
        label="現在のメールアドレス",
        widget=forms.EmailInput(attrs={'readonly': 'readonly'})  # 読み取り専用
    )
     new_email = forms.EmailField(label="新しいメールアドレス")
     confirm_email = forms.EmailField(label="新しいメールアドレス（確認用）")

     def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['current_email'].initial = user.email

     def clean(self):
        cleaned_data = super().clean()
        new_email = cleaned_data.get("new_email")
        confirm_email = cleaned_data.get("confirm_email")
        
        if new_email != confirm_email:
            raise ValidationError("新しいメールアドレスが一致しません。")
        
        return cleaned_data
     
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'stock_quantity', 'memo', 'stock_min_threshold', 'reminder']
        labels = {
            'name': 'アイテム名',
            'category': 'カテゴリ',
            'stock_quantity': '在庫数',
            'memo': 'メモ',
            'stock_min_threshold': '最低在庫数',
            'reminder': 'リマインダー',
        }



class StoreItemReferenceForm(forms.ModelForm):
    class Meta:
        model = StoreItemReference
        fields = ['price', 'unit_quantity', 'memo']
        labels = {
            'price': '価格',
            'unit_quantity': '入数',
            'memo': 'メモ',
        }

    @property
    def unit_price(self):
        price = self.cleaned_data.get('price')
        unit_quantity = self.cleaned_data.get('unit_quantity')
        return price / unit_quantity if price and unit_quantity else None

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        unit_quantity = cleaned_data.get('unit_quantity')

        # 価格と入数が両方とも入力されている場合に単価を計算
        if price is not None and unit_quantity is not None and unit_quantity > 0:
            cleaned_data['unit_price'] = price / unit_quantity
        else:
            cleaned_data['unit_price'] = None  # 単価が計算できない場合はNoneに設定

        return cleaned_data


StoreItemReferenceFormSet = modelformset_factory(
    StoreItemReference,
    fields=['store', 'price', 'unit_quantity', 'memo'],
    extra=1,  # 新しい店舗価格を追加できるフォームを1つ追加
    can_delete=True  # 削除も可能にする
)





class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'display_order']
        labels = {
            'name': 'カテゴリ名',
            'display_order': '表示順',
        }


class PurchaseHistoryForm(forms.ModelForm):
    class Meta:
        model = PurchaseHistory
        fields = ['item', 'purchased_date', 'purchased_quantity']
        labels = {
            'item': 'アイテム',
            'purchased_date': '購入日',
            'purchased_quantity': '購入数量',
        }


# 購入履歴検索
class PurchaseHistoryFilterForm(forms.Form):
        item = forms.ModelChoiceField(
        queryset=Item.objects.all().distinct(),
        required=False,
        label="アイテム名"
    )
        

# 店舗追加
class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'address', 'phone_number', 'travel_time_home_min']
        labels = {
            'name': '店舗名',
            'address': '住所',
            'phone_number': '電話番号',
            'travel_time_home_min': '自宅からの移動時間（分）',
        }

StoreTravelTimeFormSet = inlineformset_factory(
    parent_model=Store,
    model=StoreTravelTime,
    fields=['store2', 'travel_time_min'],  # 移動時間と対象店舗
    fk_name='store1',  # 親店舗（出発店舗）
    extra=1  # 新しいフォームを追加するための設定（デフォルトで1）
)

# StoreTravelTimeのフォームセット
class StoreTravelTimeForm(forms.Form):
    store_2 = forms.ModelChoiceField(queryset=Store.objects.all(), label="他店舗")
    travel_time = forms.IntegerField(label="移動時間 (分)")