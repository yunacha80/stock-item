from django import forms
from django.contrib.auth.forms import UserCreationForm,PasswordChangeForm
from App.models import User
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db import models
from django.forms import inlineformset_factory,modelformset_factory,BaseInlineFormSet,ModelForm
from .models import Item,ItemCategory,PurchaseHistory,Store,StoreTravelTime,StoreItemReference



class SignupForm(UserCreationForm):
    name = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={'placeholder': '名前'}),
        error_messages={'required': '名前は必須です。'}
    )

    email = forms.EmailField(
        label='',
        widget=forms.EmailInput(attrs={'placeholder': 'メールアドレス'}),
        error_messages={'required': 'メールアドレスは必須です。'}
    )

    password1 = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={'placeholder': 'パスワード'}),
        error_messages={'required': 'パスワードは必須です。'}
    )

    password2 = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={'placeholder': '確認用パスワード'}),
        error_messages={'required': '確認用パスワードは必須です。'}
    )

    class Meta:
        model = User
        fields = ["name", "email", "password1", "password2"]

    def clean_email(self):
        email =self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")
        return email 
    

class LoginForm(forms.Form):
    email = forms.EmailField(
        label='メールアドレス',
        error_messages={'required': 'メールアドレスは必須です。'}
    )
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(),
        error_messages={'required': 'パスワードは必須です。'}
    )

    def clean(self):
        print("ログインフォームのクリーンが呼び出された")
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        print(email, password)
        self.user = authenticate(email=email, password=password)
        if self.user is None:
            raise forms.ValidationError("メールアドレスまたはパスワードが正しくありません。")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display_order'].required = False

        
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
        help_texts = {
            'stock_min_threshold': '在庫数がこの値を下回るとアイテムが買い物リストに自動追加されます。',
            'reminder': '購入頻度を分析し、買い忘れ防ぐためのリマインダー機能',
        }

    last_purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="最終購入日",
        required=True
    )

    def clean_last_purchase_date(self):
        last_date = self.cleaned_data.get('last_purchase_date')
        if last_date and last_date > timezone.now().date():
            raise forms.ValidationError("未来の日付は選択できません。")
        return last_date

    def __init__(self, *args, store_forms=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_forms = store_forms
        self.user = user

        if user:
            self.fields['category'].queryset = ItemCategory.objects.filter(user=user)

        form_control_fields = ['name', 'category', 'stock_quantity', 'memo', 'stock_min_threshold', 'last_purchase_date']
        for field in form_control_fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['reminder'].widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        category = cleaned_data.get('category')

        if name and category:
            item_id = self.instance.id
            if Item.objects.filter(name=name, category=category, user=self.user).exclude(id=item_id).exists():
                raise ValidationError("このカテゴリには同じ名前のアイテムがすでに存在します。")

        return cleaned_data




class PurchaseHistoryForm(forms.ModelForm):
    item = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),
        widget=forms.CheckboxSelectMultiple,  # チェックボックスに変更
        label="アイテムを選択",
        required=False
    )

    class Meta:
        model = PurchaseHistory
        fields = ['item', 'purchased_date', 'purchased_quantity']
        labels = {
            'item': 'アイテム',
            'purchased_date': '購入日',
            'purchased_quantity': '購入数量',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['item'].queryset = Item.objects.filter(user=user)
        self.fields['item'].label_from_instance = lambda obj: obj.name


class StoreItemReferenceForm(forms.ModelForm):
    price_unknown = forms.BooleanField(required=False, label='価格不明')
    no_handling = forms.BooleanField(required=False, label='取り扱いなし')

    item_label = forms.CharField(
        required=False,
        label="アイテム名",
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )

    class Meta:
        model = StoreItemReference
        fields = ['item_label','price', 'price_per_unit', 'memo', 'price_unknown', 'no_handling']
        labels = {
            'price': '価格',
            'price_per_unit': '入数',
            'memo': 'メモ',
        }
        widgets = {
            'price': forms.NumberInput(attrs={'step': '1'}),
            'price_per_unit': forms.NumberInput(attrs={'step': '1'}),
            'memo': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        self.store = kwargs.pop('store', None)  # store を取り出し保持
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.item:
            self.fields['item_label'].initial = self.instance.item.name  # `item.name` をセット

        # 初期値の設定（インスタンスの値をフォームに反映）
        if self.instance and self.instance.pk:  # インスタンスが存在する場合
            self.fields['price_unknown'].initial = self.instance.price_unknown
            self.fields['no_handling'].initial = self.instance.no_handling

    def clean(self):
        cleaned_data = super().clean()
        price_unknown = cleaned_data.get('price_unknown')
        no_handling = cleaned_data.get('no_handling')
        price = cleaned_data.get('price')
        price_per_unit = cleaned_data.get('price_per_unit')

        # 「価格不明」と「取り扱いなし」が同時に選択されている場合はエラー
        if price_unknown and no_handling:
            raise forms.ValidationError("「価格不明」と「取り扱いなし」は同時に選択できません。")

        # 価格不明または取り扱いなしの場合、価格と入数をクリア
        if price_unknown or no_handling:
            cleaned_data['price'] = None
            cleaned_data['price_per_unit'] = None
        else:
            # 価格または入数が未入力の場合はエラー
            if price is None or price_per_unit is None:
                raise forms.ValidationError("価格と入数は必須です。ただし、「価格不明」または「取り扱いなし」を選択した場合は省略可能です。")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.store:  # storeが指定されている場合、インスタンスに設定
            instance.store = self.store
        if commit:
            instance.save()
        return instance

StoreItemReferenceFormSet = modelformset_factory(
    StoreItemReference,
    form=StoreItemReferenceForm,
    extra=0,
    can_delete=False,
)
    

class CustomCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = 'widgets/custom_checkbox_select.html'



class PurchaseHistoryFilterForm(forms.Form):
    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),  # デフォルトで空
        required=False,
        widget=forms.CheckboxSelectMultiple, 
        label="アイテムを選択"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['items'].queryset = Item.objects.filter(user=user)

    
        


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'address', 'phone_number', 'travel_time_home_min']
        labels = {
            'name': '店舗名(必須)',
            'address': '住所',
            'phone_number': '電話番号',
            'travel_time_home_min': '自宅からの移動時間（分）',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['travel_time_home_min'].required = True

    def clean_travel_time_home_min(self):
        value = self.cleaned_data.get('travel_time_home_min')
        if value in (None, ''):
            raise forms.ValidationError("移動時間は必須です。")
        if value <= 0:
            raise forms.ValidationError("1分以上の値を入力してください。")
        return value

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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['store_2'].queryset = Store.objects.filter(user=user).order_by('name')


StoreTravelTimeFormSet = inlineformset_factory(
    parent_model=Store,
    model=StoreTravelTime,
    fields=['store2', 'travel_time_min'],
    fk_name='store1',
    extra=1
)
