from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from App.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import inlineformset_factory,modelformset_factory,BaseInlineFormSet
from .models import Item,ItemCategory,PurchaseHistory,Store,StoreTravelTime,StoreItemReference



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
     
class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        exclude = ['user']
        fields = ['name', 'display_order']
        labels = {
            'name': 'カテゴリ名',
            'display_order': '表示順',
        }


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

    last_purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="最終購入日",
        required=True
    )


class PurchaseHistoryForm(forms.ModelForm):
    class Meta:
        model = PurchaseHistory
        fields = ['item', 'purchased_date', 'purchased_quantity']
        labels = {
            'item': 'アイテム',
            'purchased_date': '購入日',
            'purchased_quantity': '購入数量',
        }



class StoreItemReferenceForm(forms.ModelForm):
    price_unknown = forms.BooleanField(required=False, label='価格不明')
    no_price = forms.BooleanField(required=False, label='取り扱いなし')

    class Meta:
        model = StoreItemReference
        fields = ['store', 'price', 'price_per_unit', 'memo']
        labels = {
            'store': '店舗名',
            'price': '価格',
            'price_per_unit': '入数',
            'memo': 'メモ',
        }
        widgets = {
            'store': forms.TextInput(attrs={'readonly': 'readonly'}),
            'price': forms.NumberInput(attrs={'step': '1'}),
            'price_per_unit': forms.NumberInput(attrs={'step': '1'}),
            'memo': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        initial_data = kwargs.pop('initial_data', {})
        super().__init__(*args, **kwargs)
        self.fields['price_unknown'].initial = initial_data.get('price_unknown', False)
        self.fields['no_price'].initial = initial_data.get('no_price', False)

        
    def clean(self):
        cleaned_data = super().clean()
        price_unknown = cleaned_data.get('price_unknown')
        no_price = cleaned_data.get('no_price')
        price = cleaned_data.get('price')
        price_per_unit = cleaned_data.get('price_per_unit')

    # 価格不明または取り扱いなしの場合、価格をNoneに設定
        if price_unknown or no_price:
           cleaned_data['price'] = None
           cleaned_data['price_per_unit'] = None
        else:
        # 価格が未入力の場合にエラーを発生
            if price is None or price_per_unit is None:
                raise forms.ValidationError(
                    "価格と入数は必須です。ただし、価格不明または取り扱いなしを選択した場合は省略可能です。"
                    )
            
            return cleaned_data


    





class PurchaseHistoryFilterForm(forms.Form):
    """
    購入履歴検索用のフォーム
    """
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),  # 初期状態では空にする
        required=False,
        label="アイテム名"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # ユーザーを受け取る
        super().__init__(*args, **kwargs)
        if user:
            # ユーザーのアイテムに限定してクエリセットを設定
            self.fields['item'].queryset = Item.objects.filter(user=user)



        


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