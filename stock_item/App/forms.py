from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from App.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import inlineformset_factory,modelformset_factory,BaseInlineFormSet
from .models import Item,StoreItemReference, Category,PurchaseHistory,Store,StoreTravelTime,StoreItemReference



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
        fields = ['name', 'category', 'stock_quantity', 'memo', 'stock_min_threshold', 'last_purchase_date', 'reminder']
        labels = {
            'name': 'アイテム名',
            'category': 'カテゴリ',
            'stock_quantity': '在庫数',
            'memo': 'メモ',
            'stock_min_threshold': '最低在庫数',
            'last_purchase_date': '最終購入日',
            'reminder': 'リマインダー',
        }

    # 在庫数（整数）を検証
    stock_quantity = forms.IntegerField(
        min_value=0,
        label="在庫数",
        required=True,
        error_messages={'invalid': '在庫数量は整数でなければなりません。'}
    )

    # 最小在庫数（整数）を検証
    stock_min_threshold = forms.IntegerField(
        min_value=0,
        label="最低在庫数",
        required=True,
        error_messages={'invalid': '最小在庫閾値は整数でなければなりません。'}
    )

    # 最終購入日（オプション）
    last_purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="最終購入日",
        required=False
    )


# class StoreItemReferenceForm(forms.ModelForm):
#     class Meta:
#         model = StoreItemReference
#         fields = ['price', 'unit_quantity', 'memo']
#         labels = {
#             'price': '価格',
#             'unit_quantity': '入数',
#             'memo': 'メモ',
#         }

#     # 単価計算（価格 / 入数）
#     unit_price = forms.DecimalField(
#         required=False,
#         label="単価",
#         decimal_places=2,
#         max_digits=10,
#         widget=forms.NumberInput(attrs={'step': 'any'})
#     )

#     def clean(self):
#         cleaned_data = super().clean()
#         price = cleaned_data.get('price')
#         unit_quantity = cleaned_data.get('unit_quantity')

#         # unit_priceを自動的に計算
#         if price is not None and unit_quantity is not None and unit_quantity > 0:
#             cleaned_data['unit_price'] = price / unit_quantity
#         else:
#             cleaned_data['unit_price'] = None

#         return cleaned_data


# # StoreItemReferenceFormSetを定義
# StoreItemReferenceFormSet = modelformset_factory(
#     StoreItemReference,
#     fields=['price', 'unit_quantity', 'memo'],
#     extra=5,  # 新しい店舗価格を追加できるフォームを1つ追加
#     can_delete=True  # 削除も可能にする
# )

class StoreItemReferenceForm(forms.ModelForm):
    class Meta:
        model = StoreItemReference
        fields = ['store', 'price', 'unit_quantity', 'memo']
        labels = {
            'store': '店舗名',
            'price': '価格',
            'unit_quantity': '入数',
            'memo': 'メモ',
        }
        widgets = {
            'store': forms.TextInput(attrs={'readonly': 'readonly'}),
            'price': forms.NumberInput(attrs={'step': '1'}),
            'unit_quantity': forms.NumberInput(attrs={'step': '1'}),
            'memo': forms.TextInput(),
        }

class BaseStoreItemReferenceFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  # 新規アイテムの時
            for store in Store.objects.all():
                # 初期データをフォームに追加
                self.forms.append(StoreItemReferenceForm(initial={'store': store}))



StoreItemReferenceFormSet = inlineformset_factory(
    Item,
    StoreItemReference,
    form=StoreItemReferenceForm,
    formset=BaseStoreItemReferenceFormSet,
    extra=0,  # 登録店舗分だけフォームを表示
    can_delete=False,
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