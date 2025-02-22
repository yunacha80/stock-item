import json
from itertools import permutations
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction,models
from django.db.models import Min, Sum, F
from django.http import JsonResponse,HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from App.forms import SignupForm, LoginForm,EmailChangeForm,ItemForm,PurchaseHistoryFilterForm
from django.contrib.auth import login,logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse,reverse_lazy
from django import forms
from django.views.generic.edit import FormView
from .models import Item,ItemCategory,PurchaseHistory,Store,StoreTravelTime,StoreItemReference,PurchaseItem
from .forms import CustomPasswordChangeForm,ItemForm, ItemCategoryForm,PurchaseHistoryForm,StoreForm,StoreTravelTimeForm,StoreTravelTimeFormSet,StoreItemReferenceForm,StoreItemReferenceFormSet
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from collections import defaultdict
from datetime import datetime,timedelta




# Create your views here.



class PortfolioView(View):
    def get(self, request):
        return render(request, "portfolio.html")


class SignupView(View):
    def get(self, request):
        form = SignupForm()
        return render(request, "signup.html", context={
            "form":form
        })
    def post(self, request):
        print(request.POST)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
        return render(request, "signup.html", context={
            "form":form 
        })

    

class LoginView(View):
    def get(self, request):
        return render(request, "login.html")
    def post(self, request):
        print(request.POST)
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.user)
            return redirect("item_list")
        return render(request, "login.html", context={
            "form":form 
        })

class LogoutView(View):
    def get(self, request):
        logout(request)  
        return redirect("home")  
    
class PasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'password_change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('home')  # 成功時のリダイレクト先
    success_message = "パスワードが正常に変更されました。"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)  
        return super().form_valid(form)
        

class EmailChangeView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'email_change.html'
    form_class = EmailChangeForm
    success_url = reverse_lazy('home')  # 成功時のリダイレクト先
    success_message = "メールアドレスが正常に変更されました。"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  
        return kwargs

    def form_valid(self, form):
        new_email = form.cleaned_data['new_email']
        self.request.user.email = new_email 
        self.request.user.save()
        return super().form_valid(form)


class HomeView(LoginRequiredMixin, View):
    login_url = "login"
    def get(self, request):
        return render(request, "home.html")


def item_list(request):
    # 現在のユーザーを取得
    user = request.user

     # 🔹 ① 手動追加されたアイテムのIDを取得
    manually_added_items = set(PurchaseItem.objects.filter(item__user=user).values_list('item_id', flat=True))
    print(f"DEBUG (after fix - manually_added_items from PurchaseItem): {manually_added_items}")

    # 🔹 ② 在庫不足のアイテムのIDを取得
    low_stock_items = set(Item.objects.filter(user=user, stock_quantity__lt=models.F('stock_min_threshold')).values_list('id', flat=True))
    print(f"DEBUG (after fix - low_stock_items): {low_stock_items}")

    # 🔹 ③ 手動追加 & 在庫不足の両方を `shopping_list_items` に入れる
    shopping_list_items = manually_added_items | low_stock_items  # `set` の和集合で統合
    print(f"DEBUG (before item_list processing): shopping_list_items (calculated) = {shopping_list_items}")

    
    # 全アイテムとカテゴリを取得
    items = Item.objects.filter(user=user)
    categories = ItemCategory.objects.filter(user=user).order_by('display_order')

    # カテゴリ選択
    selected_category = request.GET.get('category', 'all')
    if selected_category == 'all':
        displayed_items = items
    else:
        displayed_items = items.filter(category__name=selected_category)

    # 並び替え条件
    sort_by = request.GET.get('sort', 'name_asc')
    if sort_by == 'name_asc':
        displayed_items = displayed_items.order_by('name')
    elif sort_by == 'name_desc':
        displayed_items = displayed_items.order_by('-name')
    elif sort_by == 'stock_asc':
        displayed_items = displayed_items.order_by('stock_quantity')
    elif sort_by == 'stock_desc':
        displayed_items = displayed_items.order_by('-stock_quantity')


    # アイテムデータとリマインダー条件
    item_data = []
    for item in displayed_items:
        last_purchase = item.purchase_histories.order_by('-purchased_date').first()
        last_purchase_date = last_purchase.purchased_date if last_purchase else None

        # リマインダー条件を計算
        purchase_frequency = item.purchase_interval_days or 0
        next_purchase_date = (
            last_purchase_date + timedelta(days=purchase_frequency) if last_purchase_date and purchase_frequency else None
        )
        reminder_due = (
            next_purchase_date and next_purchase_date <= now().date() and item.id not in shopping_list_items
        )

        item_data.append({
            'item': item,
            'last_purchase_date': last_purchase_date,
            'reminder_due': reminder_due,  # リマインダー表示条件
        })

    # 並び替えの適用（最終購入日順）
    if sort_by == 'date_asc':
        item_data = sorted(item_data, key=lambda x: x['last_purchase_date'] or datetime.date.min)
    elif sort_by == 'date_desc':
        item_data = sorted(item_data, key=lambda x: x['last_purchase_date'] or datetime.date.min, reverse=True)

    print(f"DEBUG (before render): shopping_list_items = {shopping_list_items}")

    return render(request, 'item_list.html', {
        'categories': categories,
        'selected_category': selected_category,
        'displayed_items': displayed_items,
        'item_data': item_data,
        'shopping_list_items': list(shopping_list_items),
        'sort_by': sort_by,
    })






@login_required
def add_item(request):

    # 現在のデフォルト `stock_min_threshold` を取得（最も古い `Item` の `stock_min_threshold` を使用）
    oldest_item = Item.objects.filter(user=request.user).order_by('created_at').first()
    stock_min_threshold_default = oldest_item.stock_min_threshold if oldest_item else 1

    stores = Store.objects.all()  # 登録済みの全店舗を取得
    store_forms = []
    has_error = False
    error_messages = []

    if request.method == 'POST':
        item_form = ItemForm(request.POST)

        if item_form.is_valid():
            # 先にアイテムを保存（これがないと item_id が NULL になる）
            item = item_form.save(commit=False)
            item.user = request.user
            item.save()

            # アイテムの購入履歴を保存（購入日が入力されている場合）
            last_purchase_date = item_form.cleaned_data.get('last_purchase_date')
            if last_purchase_date:
                purchase_history = PurchaseHistory(
                    item=item,
                    purchased_date=last_purchase_date,
                    purchased_quantity=item.stock_quantity
                )
                purchase_history.save()

            # アイテムの購入頻度を計算
            purchase_histories = PurchaseHistory.objects.filter(item=item).order_by('purchased_date')
            if purchase_histories.count() > 1:
                intervals = [
                    (purchase_histories[i].purchased_date - purchase_histories[i - 1].purchased_date).days
                    for i in range(1, purchase_histories.count())
                ]
                purchase_frequency = sum(intervals) // len(intervals)
                item.purchase_frequency = purchase_frequency
                item.save()

            # 各店舗のデータを処理
            for store in stores:
                # `get_or_create` で既存のデータを取得 or 新規作成
                store_item_reference, created = StoreItemReference.objects.get_or_create(
                    store=store, item=item
                )

                form = StoreItemReferenceForm(
                    request.POST,
                    instance=store_item_reference,
                    prefix=f"store_{store.id}"
                )
                store_forms.append(form)  

                # **バリデーションチェック**
                if not form.is_valid():
                    has_error = True
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_messages.append(f"{store.name} - {field}: {error}")

                else:
                    # 価格、価格不明、取り扱いなしのバリデーションチェック
                    price = form.cleaned_data.get('price')
                    price_unknown = form.cleaned_data.get('price_unknown', False)
                    no_price = form.cleaned_data.get('no_price', False)

                    if not price and not price_unknown and not no_price:
                        form.add_error('price', '価格を入力するか、「価格不明」または「取り扱いなし」を選択してください。')
                        has_error = True
                        error_messages.append(f"{store.name}: 価格を入力するか、「価格不明」または「取り扱いなし」を選択してください。")

            if not has_error:
                for form in store_forms:
                    store_reference = form.save(commit=False)
                    store_reference.item = item
                    store_reference.save()
                return redirect('item_list')

            else:
                print("バリデーションエラー:", error_messages)

    else:
        item_form = ItemForm(initial={"stock_min_threshold": stock_min_threshold_default})
        for store in stores:
            store_item_reference = StoreItemReference(store=store)
            form = StoreItemReferenceForm(instance=store_item_reference, prefix=f"store_{store.id}")
            store_forms.append(form)

    return render(request, 'add_item.html', {
        'item_form': item_form,
        'store_forms': store_forms,
        'error_messages': error_messages,  # **エラーメッセージをテンプレートに渡す**
    })


@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    stores = Store.objects.all()
    store_forms = []
    error_messages = []

    # 最新の購入履歴を取得
    last_purchase = PurchaseHistory.objects.filter(item=item).order_by('-purchased_date').first()
    last_purchase_date = last_purchase.purchased_date if last_purchase else None

    # 店舗ごとにフォームを作成
    for store in stores:
        store_item_reference, created = StoreItemReference.objects.get_or_create(store=store, item=item)
        
        print(f"Store: {store.name}, Item: {item.name}, Found: {not created}")
        print(f"Store: {store.name}, Price: {store_item_reference.price}, Price Per Unit: {store_item_reference.price_per_unit}")

        form = StoreItemReferenceForm(
            instance=store_item_reference,
            prefix=f"store_{store.id}",
            initial={
                'price': store_item_reference.price or 0,
                'price_per_unit': store_item_reference.price_per_unit or 1,
                'memo': store_item_reference.memo or '',
                'price_unknown': store_item_reference.price_unknown or False,
                'no_price': store_item_reference.no_price or False,
            }
        )
        store_forms.append(form)

    if request.method == 'POST':
        item_form = ItemForm(request.POST, instance=item)
        store_forms = [
            StoreItemReferenceForm(
                request.POST,
                instance=StoreItemReference.objects.get_or_create(store=store, item=item)[0],
                prefix=f"store_{store.id}"
            )
            for store in stores
        ]

        has_error = False  # バリデーションエラーがあったかどうかのフラグ

        if item_form.is_valid():
            updated_item = item_form.save(commit=False)
            updated_item.user = request.user
            updated_item.save()
        else:
            has_error = True
            for field, errors in item_form.errors.items():
                for error in errors:
                    error_messages.append(f"【{item_form.fields[field].label}】{error}")

        for form in store_forms:
            if form.is_valid():
                price = form.cleaned_data.get('price')
                price_unknown = form.cleaned_data.get('price_unknown', False)
                no_price = form.cleaned_data.get('no_price', False)

                if not price and not price_unknown and not no_price:
                    form.add_error('price', '価格を入力するか、「価格不明」または「取り扱いなし」を選択してください。')
                    has_error = True
                    error_messages.append(f"{form.instance.store.name}: 価格を入力するか、「価格不明」または「取り扱いなし」を選択してください。")
            else:
                has_error = True
                # 修正: KeyErrorを防ぐため `.get()` を使用
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{form.instance.store.name}【{form.fields.get(field, field)}】{error}")

                # 修正: `__all__` のエラー (フォーム全体のエラー) を取得
                for error in form.non_field_errors():
                    error_messages.append(f"{form.instance.store.name}: {error}")

        if not has_error:
            for form in store_forms:
                store_reference = form.save(commit=False)
                store_reference.item = updated_item
                store_reference.save()

            # 購入履歴の更新処理
            new_purchase_date = item_form.cleaned_data.get('last_purchase_date')
            if new_purchase_date:
                # `purchased_date` が同じ履歴があるか確認
                existing_history = PurchaseHistory.objects.filter(
                    item=updated_item, 
                    purchased_date=new_purchase_date
                ).first()

                if existing_history:
                    # すでに同じ `purchased_date` の履歴がある場合は、購入数量を増やす
                    existing_history.purchased_quantity += 1
                    existing_history.save()
                else:
                    # 新しい `purchased_date` の履歴を作成
                    PurchaseHistory.objects.create(
                        item=updated_item,
                        purchased_date=new_purchase_date,
                        purchased_quantity=1  # 購入数量は 1 から開始
                    )

                # 購入頻度 (purchase_interval_days) の計算
                purchase_histories = PurchaseHistory.objects.filter(item=updated_item).order_by('purchased_date')
                if purchase_histories.count() > 1:
                    intervals = [
                        (purchase_histories[i].purchased_date - purchase_histories[i - 1].purchased_date).days
                        for i in range(1, purchase_histories.count())
                    ]
                    updated_item.purchase_interval_days = sum(intervals) // len(intervals)
                    updated_item.save()

            return redirect('item_list')

        else:
            print("バリデーションエラー発生")
            for error in error_messages:
                print(error)

    else:
        item_form = ItemForm(instance=item, initial={'last_purchase_date': last_purchase_date})

    return render(request, 'edit_item.html', {
        'item_form': item_form,
        'store_forms': store_forms,
        'item': item,
        'error_messages': error_messages,
    })










def item_delete(request, item_id):
    item = get_object_or_404(Item, id=item_id, user=request.user)

    if request.method == "POST":
        print(f"Deleting item: {item.id}")  # デバッグ用出力
        item.delete()
        return JsonResponse({"success": True})  

    return JsonResponse({"success": False, "message": "無効なリクエストです。"})



def category_list(request):
    categories = ItemCategory.objects.filter(user=request.user)
    if not categories:
        print("現在、カテゴリは存在しません。")  # デバッグ用の出力
    return render(request, 'category_list.html', {'categories': categories})

def categorized_item_list(request):
    items = Item.objects.filter(user=request.user)
    items_by_category = defaultdict(list)
    for item in items:
        items_by_category[item.category.name].append(item)
    return render(request, 'item_list.html', {'items_by_category': items_by_category})

@login_required
def category_add(request):
    if request.method == "POST":
        form = ItemCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            # カテゴリ数をチェック
            if ItemCategory.objects.filter(user=request.user).count() >= 10:
                messages.error(request, "カテゴリは最大10個まで登録可能です。")
                return render(request, 'category_form.html', {'form': form})
            category.save()
            messages.success(request, "カテゴリが追加されました。")
            return redirect('settings')
        else:
            messages.error(request, "入力内容に誤りがあります。")
    else:
        form = ItemCategoryForm()
    return render(request, 'category_form.html', {'form': form})





# カテゴリ編集
def category_edit(request, category_id):
    category = get_object_or_404(ItemCategory, id=category_id)
    if request.method == "POST":
        form = ItemCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = ItemCategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form})


def category_delete(request, category_id):
    category = get_object_or_404(ItemCategory, id=category_id)
    if request.method == "POST":
        category.delete()
        return redirect('settings')
    return render(request, 'category_confirm_delete.html', {'category': category})



# 購入履歴
# 購入履歴をグループ化してデバッグ出力
def purchase_history_list(request):
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')

    # 購入日でグループ化
    grouped_histories = defaultdict(list)
    for history in histories:
        dateStr = datetime.strftime(history.purchased_date, "%Y-%m-%d")
        grouped_histories[dateStr].append(history)

    return render(
        request,
        "purchase_history_list.html",
        {
            "grouped_histories": dict(grouped_histories),
        },
    )



# 購入履歴検索
def purchase_history_Search(request):
    form = PurchaseHistoryFilterForm(user=request.user, data=request.GET)

    # 全購入履歴を取得
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')

    if form.is_valid() and form.cleaned_data['items']:
        print("選択されたアイテム:", form.cleaned_data['items'])
        histories = histories.filter(item__in=form.cleaned_data['items'])

    # 日付でグループ化
    grouped_histories = defaultdict(list)
    for history in histories:
        grouped_histories[history.purchased_date].append(history)

    # グループ化された履歴をデバッグ出力
    print("グループ化された履歴:")
    for date, group in grouped_histories.items():
        print(f"日付: {date}, 件数: {len(group)}")
        for h in group:
            print(f"  - アイテム: {h.item.name}, 数量: {h.purchased_quantity}")

    return render(request, 'purchase_history_list.html', {
    'grouped_histories': dict(grouped_histories),  
    'form': form
    })







# 店舗一覧
def store_list(request):
    stores = Store.objects.filter(user=request.user)
    if not stores.exists():
        messages.info(request, "登録された店舗がありません。")    
    return render(request, 'store_list.html', {'stores': stores})



def store_delete(request, store_id):
    store = get_object_or_404(Store, id=store_id, user=request.user)
    if request.method == "POST":
        store.delete()
        messages.success(request, "店舗が削除されました。")
        return redirect('store_list') 
    return render(request, 'store_confirm_delete.html', {'store': store})



def add_store_travel_time(request):
    if request.method == 'POST':
        form = StoreTravelTimeFormSet(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "移動時間が追加されました。")
            return redirect('store_list')
        else:
            messages.error(request, "フォームにエラーがあります。")
    else:
        form = StoreTravelTimeFormSet()
    return render(request, 'store_add.html', {'form': form})

# 新規店舗追加
def store_add(request):
    stores = Store.objects.filter(user=request.user) 

    if request.method == 'POST':
        store_form = StoreForm(request.POST)

        if store_form.is_valid():
            try:
                with transaction.atomic():  
                    store = store_form.save(commit=False)
                    store.user = request.user
                    store.save()

                    # 他店舗との移動時間を保存
                    for store_instance in stores:
                        travel_time_key = f"travel_time_{store_instance.id}"
                        if travel_time_key in request.POST:
                            travel_time = request.POST[travel_time_key]

                            # 移動時間を保存
                            StoreTravelTime.objects.create(
                                store1=store,
                                store2=store_instance,
                                travel_time_min=travel_time
                            )
                            StoreTravelTime.objects.create(
                                store1=store_instance,
                                store2=store,
                                travel_time_min=travel_time
                            )

                    messages.success(request, "店舗が追加されました。")
                    return redirect('settings')

            except Exception as e:
                print(f"Error: {e}")
                messages.error(request, "店舗の追加中にエラーが発生しました。")
            
    else:
        store_form = StoreForm()

    return render(request, 'store_add.html', {'store_form': store_form, 'stores': stores})

def store_edit(request, pk):
    """
    店舗編集ビュー: 店舗情報、移動時間、アイテム価格を編集
    """
    store = get_object_or_404(Store, pk=pk)

    # 店舗情報フォーム
    store_form = StoreForm(instance=store)

    # 他店舗一覧（現在の店舗を除外）
    other_stores = Store.objects.exclude(id=store.id)

    # 既存の移動時間データを辞書に格納
    travel_times = {tt.store2.id: tt for tt in StoreTravelTime.objects.filter(store1=store)}

    # フォームセットデータを辞書で渡す
    travel_time_forms = []
    for other_store in other_stores:
        form = StoreTravelTimeForm(
            initial={
                "store2": other_store.id,
                "travel_time_min": travel_times.get(other_store.id).travel_time_min if other_store.id in travel_times else "",
            }
        )
        travel_time_forms.append({"store": other_store, "form": form})

    # アイテム価格フォームセット
    item_price_formset = StoreItemReferenceFormSet(
        queryset=StoreItemReference.objects.filter(store=store).select_related("item")
    )

    if request.method == "POST":
        store_form = StoreForm(request.POST, instance=store)
        item_price_formset = StoreItemReferenceFormSet(request.POST, queryset=StoreItemReference.objects.filter(store=store).select_related("item"))

        # 他店舗の移動時間データを取得
        for tf in travel_time_forms:
            tf["form"] = StoreTravelTimeForm(request.POST)

        if store_form.is_valid() and all(tf["form"].is_valid() for tf in travel_time_forms) and item_price_formset.is_valid():
            store_form.save()

            # 移動時間の保存
            for tf in travel_time_forms:
                travel_time_instance, created = StoreTravelTime.objects.get_or_create(
                    store1=store,
                    store2=tf["store"],
                    defaults={"travel_time_min": tf["form"].cleaned_data["travel_time_min"]},
                )
                if not created:
                    travel_time_instance.travel_time_min = tf["form"].cleaned_data["travel_time_min"]
                    travel_time_instance.save()

            item_price_formset.save()
            return redirect("settings")

    return render(
        request,
        "store_edit.html",
        {
            "form": store_form,
            "travel_time_forms": travel_time_forms,
            "item_price_formset": item_price_formset,
            "no_items": not StoreItemReference.objects.filter(store=store).exists(),
        },
    )







from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Item, ItemCategory, Store

@login_required
def settings_view(request):
    """
    設定画面ビュー
    """
    # 現在のデフォルト値を取得（最も古い `Item` の `stock_min_threshold` を基準とする）
    oldest_item = Item.objects.filter(user=request.user).order_by('created_at').first()
    stock_min_threshold_default = oldest_item.stock_min_threshold if oldest_item else 1

    stores = Store.objects.all()
    categories = ItemCategory.objects.filter(user=request.user).order_by('display_order')

    if request.method == "POST":
        if "update_stock_threshold" in request.POST:
            # 在庫最低値の一括変更（変更されていない `stock_min_threshold` を更新）
            new_value = request.POST.get("stock_min_threshold", None)
            if new_value is not None:
                try:
                    new_value = int(new_value)
                    if new_value > 0:  # 正の整数のみ許可
                        items_to_update = Item.objects.filter(
                            user=request.user,
                            stock_min_threshold=stock_min_threshold_default  # 変更されていないアイテムのみ対象
                        )
                        if items_to_update.exists():
                            for item in items_to_update:
                                item.stock_min_threshold = new_value
                            Item.objects.bulk_update(items_to_update, ["stock_min_threshold"])
                            messages.success(request, f"変更されていないアイテムの在庫最低値を {new_value} に更新しました。")
                        else:
                            messages.warning(request, "変更対象のアイテムがありません。")
                except ValueError:
                    messages.error(request, "無効な値が入力されました。")

        # カテゴリ追加処理
        if "add_category" in request.POST:
            category_name = request.POST.get("category_name", "").strip()
            if category_name:
                ItemCategory.objects.create(user=request.user, name=category_name)
                messages.success(request, f"カテゴリ '{category_name}' を追加しました。")

    return render(request, "settings.html", {
        "stock_min_threshold_default": stock_min_threshold_default,
        "categories": categories,
        "stores": stores
    })





# @login_required
# @require_POST
# def update_stock_min_threshold(request):
#     """デフォルトの在庫最低値を更新"""
#     try:
#         new_threshold = request.POST.get("stock_min_threshold")

#         if not new_threshold:
#             raise ValueError("在庫最低値が空です。")

#         if not new_threshold.isdigit():
#             raise ValueError("在庫最低値は数値でなければなりません。")

#         new_threshold = int(new_threshold)
#         if new_threshold <= 0:
#             raise ValueError("在庫最低値は正の整数でなければなりません。")

#         # デフォルト設定を取得または作成
#         default_setting, created = DefaultSettings.objects.get_or_create(id=1)
#         default_setting.stock_min_threshold_default = new_threshold
#         default_setting.save()

#         messages.success(request, f"デフォルトの在庫最低値を {new_threshold} に更新しました。")

#     except ValueError as e:
#         messages.error(request, f"エラー: {e}")
#     except Exception as e:
#         messages.error(request, f"予期しないエラーが発生しました: {e}")

#     return redirect("settings")



@login_required
@require_POST
def update_stock(request):
    """
    在庫数を更新するエンドポイント（リロード後も反映）
    """
    try:
        data = json.loads(request.body)  # リクエストボディの JSON を解析
        item_id = data.get("item_id")
        delta = int(data.get("delta", 0))  # 増減数

        if not item_id or delta == 0:
            return JsonResponse({"success": False, "message": "不正なリクエスト"}, status=400)

        # `Item` モデルの `stock_quantity` を更新
        item = get_object_or_404(Item, id=item_id, user=request.user)
        item.stock_quantity = max(0, item.stock_quantity + delta)  # マイナスにならないよう制限
        item.save()  # 変更をデータベースに保存

        return JsonResponse({"success": True, "new_stock": item.stock_quantity})

    except Item.DoesNotExist:
        return JsonResponse({"success": False, "message": "アイテムが見つかりません"}, status=404)

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# @login_required
# def reset_hidden_items(request):
#     """
#     非表示リストをリセットして全アイテムを再表示、または特定のアイテムを非表示にする
#     """
#     if request.method == "POST":
#         item_id = request.POST.get("item_id")  # 非表示にしたいアイテムIDを取得

#         if item_id:  # 特定のアイテムを非表示
#             hidden_items = request.session.get("hidden_items", [])
#             if item_id not in hidden_items:
#                 hidden_items.append(item_id)  # 非表示リストに追加
#                 request.session["hidden_items"] = hidden_items
#                 messages.success(request, f"アイテムID {item_id} を買い物リストから非表示にしました。")
#             else:
#                 messages.info(request, "このアイテムはすでに非表示リストに追加されています。")
#         else:  # 非表示リストをリセット（すべて再表示）
#             request.session["hidden_items"] = []
#             messages.success(request, "非表示リストがリセットされました。")

#     return redirect("shopping_list")




def calculate_travel_time(cleaned_route, travel_times):
    """
    総移動時間を計算する関数。
    - cleaned_route: 整理されたルート（店舗のリスト）
    - travel_times: 店舗間の移動時間の辞書
    """
    total_time = 0

    if not cleaned_route:
        return total_time

    # 自宅 → 最初の店舗
    total_time += cleaned_route[0].travel_time_home_min

    # 店舗間の移動
    for i in range(len(cleaned_route) - 1):
        travel_time = travel_times.get((cleaned_route[i], cleaned_route[i + 1]), None)
        if travel_time is not None:
            total_time += travel_time
        else:
            print(f"DEBUG: Travel time missing between {cleaned_route[i].name} and {cleaned_route[i + 1].name}")

    # 最後の店舗 → 自宅
    total_time += cleaned_route[-1].travel_time_home_min

    return total_time




# def calculate_lowest_price_route(purchase_items):
#     results = {}
#     missing_items = []
#     total_price = 0
#     unit_total_price = 0
#     store_details = {}
#     route = []
#     travel_times = {}

#     print(f"DEBUG: Received purchase_items: {[item.name for item in purchase_items]}")

#     # 店舗間の移動時間
#     stores = Store.objects.all()
#     for store1 in stores:
#         for store2 in stores:
#             if store1 != store2:
#                 travel_time = StoreTravelTime.objects.filter(
#                     store1=store1, store2=store2
#                 ).first()
#                 travel_times[(store1, store2)] = travel_time.travel_time_min if travel_time else None
#                 print(f"DEBUG: Travel time between {store1.name} and {store2.name}: {travel_times[(store1, store2)]}")

#     for purchase_item in purchase_items:
#         item = purchase_item.item
#         references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)
#         print(f"DEBUG: References for item '{item.name}': {[{'store': ref.store.name, 'price': ref.price, 'ppu': ref.price_per_unit} for ref in references]}")

#         if not references.exists():
#             missing_items.append(item.name)
#             continue

#         # 最適なリファレンスを選択
#         best_reference = min(references, key=lambda ref: ref.price / ref.price_per_unit)
#         print(f"DEBUG: Best reference for '{item.name}': {{'store': {best_reference.store.name}, 'unit_price': {best_reference.price / best_reference.price_per_unit}}}")


#         store = best_reference.store
#         unit_price = best_reference.price / best_reference.price_per_unit
#         item_total_price = best_reference.price * purchase_item.planned_purchase_quantity
#         print(f"DEBUG: Calculated item_total_price for '{item.name}': {item_total_price} (unit_price: {unit_price}, planned_quantity: {item.planned_purchase_quantity})")

#         # 結果に追加
#         results[item.name] = {
#             'store': store.name,
#             'unit_price': unit_price,
#             'price': item_total_price,
#             'quantity': item.planned_purchase_quantity,
#         }

#         # ルートの店舗を更新
#         if store not in route:
#             route.append(store)

#         # 店舗ごとの商品詳細
#         if store.name not in store_details:
#             store_details[store.name] = []
#         store_details[store.name].append({
#             'name': item.name,
#             'quantity': item.planned_purchase_quantity,
#             'unit_price': unit_price,
#         })

#         # 合計金額を更新
#         total_price += item_total_price
#         unit_total_price += unit_price

#     # ルート計算
#     print(f"DEBUG: Route before cleaning: {[store.name for store in route]}")
#     cleaned_route = clean_route(route)

#     print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
#     print(f"DEBUG: Travel Times Dictionary: {travel_times}")
#     total_travel_time = calculate_travel_time(cleaned_route, travel_times)
#     print(f"DEBUG: Total Travel Time: {total_travel_time}")

#     # 最終結果のデバッグ
#     print(f"DEBUG: Results: {results}")
#     print(f"DEBUG: Missing Items: {missing_items}")
#     print(f"DEBUG: Total Price: {total_price}")
#     print(f"DEBUG: Unit Total Price: {unit_total_price}")
#     print(f"DEBUG: Store Details: {store_details}")

#     return results, total_travel_time, missing_items, total_price, unit_total_price, store_details




# def calculate_shortest_time_route(purchase_items):
#     """
#     最短時間提案の計算。
#     """
#     results = {}
#     route = []
#     missing_items = []
#     total_price = 0
#     unit_total_price = 0
#     store_details = {}
#     travel_times = {}

    
#     stores = Store.objects.all()
#     for store1 in stores:
#         for store2 in stores:
#             if store1 != store2:
#                 travel_time = StoreTravelTime.objects.filter(store1=store1, store2=store2).first()
#                 if travel_time:
#                     travel_times[(store1, store2)] = travel_time.travel_time_min

#     # 商品ごとに最短時間の店舗を選定
#     for item in purchase_items:
#         references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)

#         if not references.exists():
#             missing_items.append(item.name)
#             continue

#         valid_stores = [ref.store for ref in references]
#         best_store = min(valid_stores, key=lambda store: store.travel_time_home_min)

#         best_reference = references.filter(store=best_store).first()
#         item_price = (best_reference.price or 0) * item.planned_purchase_quantity

#         unit_price = best_reference.price / best_reference.price_per_unit if best_reference.price_per_unit else 0

#         results[item.name] = {
#             'store': best_store.name,
#             'travel_time': best_store.travel_time_home_min,
#             'price': item_price,
#             'quantity': item.planned_purchase_quantity,
#         }

#         if best_store not in route:
#             route.append(best_store)

#         # 店舗ごとの商品詳細
#         if best_store.name not in store_details:
#             store_details[best_store.name] = []
#         store_details[best_store.name].append({
#             'name': item.name,
#             'quantity': item.planned_purchase_quantity,
#             'unit_price': unit_price,
#         })

#         total_price += item_price
#         unit_total_price += unit_price

#     # 移動時間の計算
#     cleaned_route = clean_route(route)
#     total_travel_time = calculate_travel_time(cleaned_route, travel_times)

#     # デバッグ用出力
#     print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
#     print(f"DEBUG: Travel Times: {travel_times}")
#     print(f"DEBUG: Total Travel Time: {total_travel_time}")

#     return results, total_travel_time, missing_items, total_price, unit_total_price, store_details




# def calculate_best_balance_route(purchase_items):
#     balance_results = {}
#     combined_total_price = 0
#     combined_unit_total = 0
#     store_details = {}
#     route = []
#     travel_times = {}

#     # 店舗間の移動時間を準備
#     stores = Store.objects.all()
#     for store1 in stores:
#         for store2 in stores:
#             if store1 != store2:
#                 travel_time = StoreTravelTime.objects.filter(store1=store1, store2=store2).first()
#                 if travel_time:
#                     travel_times[(store1, store2)] = travel_time.travel_time_min

#     # 各商品の最適店舗を選択しスコアを計算
#     for item in purchase_items:
#         references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)

#         if not references.exists():
#             continue

#         # スコア計算 (価格と移動時間のバランス)
#         best_reference = min(references, key=lambda ref: 0.6 * ref.price + 0.4 * ref.store.travel_time_home_min)
#         best_store = best_reference.store
#         route.append(best_store)

#         item_price = (best_reference.price or 0) * item.planned_purchase_quantity


#         unit_price = best_reference.price / best_reference.price_per_unit if best_reference.price_per_unit else 0

#         combined_total_price += item_price
#         combined_unit_total += unit_price

#         balance_results[item.name] = {
#             'store': best_store.name,
#             'score': 0.6 * item_price + 0.4 * best_store.travel_time_home_min,
#             'price': item_price,
#             'quantity': item.planned_purchase_quantity,
#         }

#         # 店舗ごとの商品詳細を構築
#         if best_store.name not in store_details:
#             store_details[best_store.name] = []
#         store_details[best_store.name].append({
#             'name': item.name,
#             'quantity': item.planned_purchase_quantity,
#             'unit_price': unit_price,
#         })

#     # ルート内の重複店舗を削除
#     cleaned_route = clean_route(route)

#     # 総移動時間を計算
#     total_travel_time = calculate_travel_time(cleaned_route, travel_times)

#     # デバッグ用出力
#     print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
#     print(f"DEBUG: Total Travel Time: {total_travel_time}")

#     # 未購入品リストは未処理アイテムから生成
#     combined_missing = [item.name for item in purchase_items if item.name not in balance_results]

#     return balance_results, combined_missing, combined_total_price, combined_unit_total, store_details, total_travel_time



def calculate_route(purchase_items, strategy, consider_missing=True):
    """
    買い回りルートの計算 (自宅↔店舗の移動時間も考慮)
    """
    results, missing_items, total_price, unit_total_price = {}, [], 0, 0
    store_details, travel_times = {}, {}

    # 1. 店舗間の移動時間を取得
    stores = Store.objects.all()
    for store1 in stores:
        for store2 in stores:
            if store1 != store2:
                travel_time = StoreTravelTime.objects.filter(store1=store1, store2=store2).first()
                travel_times[(store1, store2)] = travel_time.travel_time_min if travel_time else float("inf")

    # 2. 商品ごとに最適な購入店舗を決定
    store_item_map = {}  # {store: [items]}

    for purchase_item in purchase_items:
        item = purchase_item.item

        # 価格情報がある `StoreItemReference` を取得（更新日時が最新のものを優先）
        references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None).order_by('-updated_at')

        # 価格不明・取扱いなしを除外する場合の処理
        if not consider_missing:
            valid_references = references.exclude(price_unknown=True, no_price=True)
        else:
            valid_references = references

        # **価格情報が全くない場合、missing_items に追加**
        if not valid_references.exists():
            print(f"DEBUG: {item.name} は価格情報なしのため missing_items に追加")
            missing_items.append(item.name)
            if not consider_missing:
                continue

        # 提案ルート戦略ごとに最適なリファレンスを選択
        if strategy == "price":
            best_reference = min(valid_references, key=lambda ref: ref.price / ref.price_per_unit)
        elif strategy == "time":
            best_reference = min(valid_references, key=lambda ref: ref.store.travel_time_home_min + min(travel_times.get((ref.store, other), float("inf")) for other in stores))
        elif strategy == "balance":
            best_reference = min(valid_references, key=lambda ref: 0.6 * (ref.price / ref.price_per_unit) + 0.4 * (ref.store.travel_time_home_min + min(travel_times.get((ref.store, other), float("inf")) for other in stores)))
        else:
            continue

        store = best_reference.store
        unit_price = best_reference.price / best_reference.price_per_unit
        quantity = purchase_item.planned_purchase_quantity or 1
        item_total_price = best_reference.price * quantity

        results[item.name] = {
            'store': store.name,
            'unit_price': unit_price,
            'price': item_total_price,
            'quantity': quantity,
        }

        if store not in store_item_map:
            store_item_map[store] = []
        store_item_map[store].append(item)

        if store.name not in store_details:
            store_details[store.name] = []
        store_details[store.name].append({
            'name': item.name,
            'quantity': quantity,
            'unit_price': unit_price,
        })

        total_price += item_total_price
        unit_total_price += unit_price

    selected_stores = list(store_item_map.keys())

    if not selected_stores:
        print("DEBUG: 選択された店舗がありません。ルート計算をスキップします。")

        return {
            "details": {},
            "route": [],
            "total_price": 0,
            "unit_total_price": 0,
            "total_time": 0,
            "store_details": {},
            "missing_items": missing_items if consider_missing else [],
            "no_suggestions": True,  # 価格不明・取扱いなしのみの場合のフラグを追加
        }

    print(f"DEBUG: selected_stores = {[store.name for store in selected_stores]}")

    best_route = min(
        permutations(selected_stores),
        key=lambda r: (
            sum(travel_times.get((r[i], r[i+1]), float("inf")) for i in range(len(r)-1)) 
            + r[0].travel_time_home_min  
            + r[-1].travel_time_home_min  
        )
    )

    total_travel_time = (
        sum(travel_times.get((best_route[i], best_route[i+1]), float("inf")) for i in range(len(best_route)-1))
        + (best_route[0].travel_time_home_min if best_route else 0)  
        + (best_route[-1].travel_time_home_min if best_route else 0)  
    )
    print(f"DEBUG: missing_items = {missing_items}")

    
    return {
        "details": results,
        "route": best_route,
        "total_price": total_price,
        "unit_total_price": unit_total_price,
        "total_time": total_travel_time,
        "store_details": store_details,
        "missing_items": missing_items if consider_missing else [],
         "no_suggestions": False,
    }













def clean_route(route):
    """
    ルート内の店舗を順序を維持したまま整形し、重複を排除。
    """
    cleaned_route = []
    for store in route:
        if not cleaned_route or cleaned_route[-1] != store:
            cleaned_route.append(store)
    # 最初と最後の店舗が同じ場合、最後を削除
    if len(cleaned_route) > 1 and cleaned_route[0] == cleaned_route[-1]:
        cleaned_route.pop()
    return cleaned_route



@login_required
@require_POST
@csrf_exempt
def remove_from_shopping_list(request, item_id):
    """
    買い物リストからアイテムを削除（PurchaseItem を削除）
    """
    try:
        print(f"DEBUG: remove_from_shopping_list called with item_id={item_id}")

        # 1. 手動追加されたアイテムを削除
        purchase_item = PurchaseItem.objects.filter(item__id=item_id, item__user=request.user)
        if purchase_item.exists():
            purchase_item.delete()
            print(f"DEBUG: 手動追加アイテム {item_id} を削除")
            return JsonResponse({"success": True, "message": "手動追加アイテムを削除しました。"})

        # 2. 自動追加アイテムの場合、stock_min_threshold を調整して削除
        item = get_object_or_404(Item, id=item_id, user=request.user)
        item.stock_min_threshold = item.stock_quantity  # 在庫数と同じにすることでリストから削除
        item.save()

        print(f"DEBUG: 自動追加アイテム {item_id} の stock_min_threshold を変更し、リストから削除")
        return JsonResponse({"success": True, "message": "自動追加アイテムを削除しました。"})

    except Exception as e:
        print(f"DEBUG: 削除エラー - {e}")
        return JsonResponse({"success": False, "message": f"削除に失敗しました: {e}"}, status=500)








def suggestion_detail_view(request, suggestion_type):
    """
    提案の詳細表示画面。
    """
    # 提案の種類（最安値、最短時間、バランス）に基づいてデータを取得
    suggestion = {
        "type": suggestion_type,
        "details": f"{suggestion_type} に基づく提案詳細情報。",
        "route": ["Store A", "Store B", "Store C"],
        "total_price": 2000 if suggestion_type == "最安値" else None,
        "total_time": 30 if suggestion_type == "最短時間" else None,
    }

    return render(request, "suggestion_detail.html", {
        "suggestion": suggestion,
    })

@login_required
@require_POST
def add_to_shopping_list(request):
    """
    在庫不足のアイテムを自動追加
    手動で追加するアイテムを処理
    """
    try:
        raw_body = request.body
        print(f"DEBUG: Raw Request Body: {raw_body}")

        data = json.loads(raw_body)
        item_id = data.get("item_id")
        purchase_quantity = data.get("purchase_quantity", 1)  # ユーザーが指定した購入予定数（デフォルト: 1）
        print(f"DEBUG: item_id={item_id}, purchase_quantity={purchase_quantity}")
    except json.JSONDecodeError:
        print("DEBUG: JSON デコードエラー")
        return JsonResponse({"message": "無効なリクエスト形式"}, status=400)

    added_items = []

    if item_id:
        print(f"DEBUG: 手動追加開始 (item_id={item_id})")

        try:
            item = get_object_or_404(Item, id=item_id, user=request.user)
            print(f"DEBUG: item={item.name}, stock_quantity={item.stock_quantity}, stock_min_threshold={item.stock_min_threshold}")

            # 🔹 get_or_create を使用して重複登録を防ぐ
            purchase_item, created = PurchaseItem.objects.get_or_create(
                item=item,
                defaults={"planned_purchase_quantity": purchase_quantity}  # ユーザーが指定した数を適用
            )

            if created:
                added_items.append(item.name)
                print(f"DEBUG: 手動追加成功 {item.name} (item_id={item_id})")
                return JsonResponse({
                    "message": f"{item.name} を買い物リストに追加しました。",
                    "success": True,
                    "planned_purchase_quantity": purchase_item.planned_purchase_quantity
                })
            else:
                print(f"DEBUG: {item.name} はすでに買い物リストに追加済み")
                return JsonResponse({
                    "message": f"{item.name} はすでに買い物リストに追加されています。",
                    "success": False,
                    "planned_purchase_quantity": purchase_item.planned_purchase_quantity  # 既存の値を返す
                })

        except Exception as e:
            print(f"DEBUG: 手動追加中にエラー発生: {e}")
            return JsonResponse({"message": "アイテム追加中にエラーが発生しました。"}, status=500)

    # 自動追加の処理
    items_to_add = Item.objects.filter(
        user=request.user, stock_quantity__lt=models.F("stock_min_threshold")
    )

    for item in items_to_add:
        purchase_item, created = PurchaseItem.objects.get_or_create(
            item=item,
            defaults={"planned_purchase_quantity": max(1, item.stock_min_threshold - item.stock_quantity)}
        )
        if created:
            added_items.append(item.name)

    print(f"DEBUG: 自動追加 {len(added_items)} 個のアイテムを買い物リストに追加")

    return JsonResponse({
        "message": f"{len(added_items)} 個のアイテムが買い物リストに追加されました。",
        "success": True,
        "added_items": added_items
    })



# 買い物リスト内での手動アイテム追加
@login_required
def add_shopping_item(request):
    """
    買い物リストにアイテムを追加するためのビュー。
    """
    items = Item.objects.filter(user=request.user)  # ユーザーの全アイテムを取得

    if request.method == "POST":
        selected_item_id = request.POST.get("item_id")
        quantity = request.POST.get("quantity")

        if not selected_item_id or not quantity:
            messages.error(request, "アイテムと数量を入力してください。")
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    raise ValueError("数量は1以上にしてください。")

                item = Item.objects.get(id=selected_item_id, user=request.user)
                # 在庫最低値を更新（買い物リストに反映）
                item.stock_min_threshold = item.stock_quantity + quantity
                item.save()

                messages.success(request, f"{item.name} を買い物リストに {quantity} 個追加しました。")
                return redirect("shopping_list")
            except ValueError:
                messages.error(request, "無効な数量です。")
            except Item.DoesNotExist:
                messages.error(request, "選択したアイテムが見つかりません。")

    return render(request, "add_shopping_item.html", {
        "items": items,
    })


@login_required
@require_POST
def update_purchase_quantity(request):
    """
    購入予定数を更新するAPI
    """
    try:
        data = json.loads(request.body)
        item_id = data.get("item_id")
        new_quantity = data.get("new_quantity")

        if not item_id or not isinstance(new_quantity, int) or new_quantity < 0:
            return JsonResponse({"message": "無効なリクエスト"}, status=400)

        item = get_object_or_404(Item, id=item_id, user=request.user)
        
        # `PurchaseItem` を明示的に取得 or 作成
        purchase_item, created = PurchaseItem.objects.get_or_create(item=item, defaults={"planned_purchase_quantity": new_quantity})

        # 既存データがある場合は更新
        purchase_item.planned_purchase_quantity = new_quantity
        purchase_item.save()

        print(f"DEBUG: {item.name} の購入予定数を {new_quantity} に更新")

        return JsonResponse({
            "message": f"{item.name} の購入予定数を {new_quantity} に更新しました。",
            "success": True,
            "planned_purchase_quantity": purchase_item.planned_purchase_quantity
        })

    except json.JSONDecodeError:
        return JsonResponse({"message": "無効なリクエスト形式"}, status=400)

    except Exception as e:
        print(f"DEBUG: 購入予定数変更エラー - {e}")
        return JsonResponse({"message": "購入予定数の更新中にエラーが発生しました。"}, status=500)

@login_required
def shopping_list_view(request):
    """
    買い物リストの表示、購入済み処理、提案生成を管理。
    """  
    manually_added_items = PurchaseItem.objects.filter(item__user=request.user).distinct()
    manually_added_item_ids = set(manually_added_items.values_list("item_id", flat=True))

    # 自動追加アイテムを取得
    low_stock_items = Item.objects.filter(
        user=request.user, stock_quantity__lt=models.F('stock_min_threshold')
    )

    # すべてのアイテムに `planned_purchase_quantity` を適用
    final_items = []
    for item in low_stock_items:
        purchase_item = manually_added_items.filter(item=item).first()
        planned_quantity = purchase_item.planned_purchase_quantity if purchase_item else max(1, item.stock_min_threshold - item.stock_quantity)

        item.planned_purchase_quantity = planned_quantity
        final_items.append(item)

    for purchase_item in manually_added_items:
        if purchase_item.item.id not in [item.id for item in final_items]:
            purchase_item.item.planned_purchase_quantity = purchase_item.planned_purchase_quantity
            final_items.append(purchase_item.item)

    shopping_list_items = manually_added_item_ids.union(low_stock_items.values_list("id", flat=True))

    print(f"DEBUG: shopping_list_items = {shopping_list_items}")


    # 提案結果、メッセージ、選択アイテム
    suggestions = []
    feedback_messages = []
    selected_items = []

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "suggest":
            selected_item_ids = request.POST.getlist("item_ids")
            if selected_item_ids:
                purchase_items = PurchaseItem.objects.filter(item__id__in=selected_item_ids, item__user=request.user)

                #  取り扱いなし含む（通常の最安値計算）
                price_suggestion = calculate_route(purchase_items, "price", consider_missing=True)

                # 取り扱いなし無視（価格不明商品を無視する最安値計算）
                price_suggestion_ignore = calculate_route(purchase_items, "price", consider_missing=False)

                #  最短時間・安値＋短時間も計算
                time_suggestion = calculate_route(purchase_items, "time", consider_missing=True)
                balance_suggestion = calculate_route(purchase_items, "balance", consider_missing=True)

                suggestions = [
                    {
                        "type": "最安値",
                        **price_suggestion,
                    },
                    {
                        "type": "最安値 (取扱なし無視)",
                        **price_suggestion_ignore,
                    },
                    {
                        "type": "最短時間",
                        **time_suggestion,
                    },
                    {
                        "type": "安値＋短時間",
                        **balance_suggestion,
                    },
            ]
            print(f"DEBUG: 取扱いなし無視 (price_suggestion_ignore): {price_suggestion_ignore['missing_items']}")

        # **在庫更新**
        elif action == "update":
            for item in final_items:
                purchased_quantity = request.POST.get(f"purchased_quantity_{item.id}", None)
                purchased_date = request.POST.get(f"purchased_date_{item.id}", None)

                if purchased_quantity and purchased_date:
                    try:
                        purchased_quantity = int(purchased_quantity)
                        purchased_date = datetime.strptime(purchased_date, "%Y-%m-%d").date()

                        # 在庫更新
                        item.stock_quantity += purchased_quantity
                        item.save()

                        # 購入履歴を記録
                        PurchaseHistory.objects.create(
                            item=item,
                            purchased_quantity=purchased_quantity,
                            purchased_date=purchased_date,
                        )

                        # 在庫が最低在庫数を満たした場合、リストから削除
                        if item.stock_quantity >= item.stock_min_threshold:
                            PurchaseItem.objects.filter(item=item).delete()

                        messages.success(request, f"{item.name} の在庫を更新しました。")

                    except Exception as e:
                        messages.error(request, f"{item.name} の在庫更新中にエラーが発生しました: {e}")
                        print(f"DEBUG: Error: {e}")
                    return redirect("shopping_list")

        elif "delete_item" in request.POST:
            delete_item_id = request.POST.get("delete_item")
            if delete_item_id:
                PurchaseItem.objects.filter(item_id=delete_item_id, item__user=request.user).delete()
                return redirect("shopping_list")
    print(f"DEBUG: 最終 items (final_items) = {[item.id for item in final_items]}")

    missing_items = []
    if suggestions:
        for suggestion in suggestions:
            missing_items.extend(suggestion.get("missing_items", []))

    context = {
        "suggestions": suggestions,
        "missing_items": list(set([item for s in suggestions for item in s.get("missing_items", [])]))  # 重複削除
        }
    print(f"DEBUG: View に渡す missing_items = {context['missing_items']}")  
    

    
    

            
    return render(request, "shopping_list.html", {
        "items": final_items,
        "suggestions": suggestions,
        "messages": feedback_messages,
        "selected_items": selected_items,
        "shopping_list_items":  list(shopping_list_items),
    })




@login_required
@csrf_exempt
def update_stock_and_check(request):
    """
    購入済みがチェックされたアイテムのみ在庫を更新し、最低在庫数を上回った場合にリストから削除。
    """
    if request.method == "POST":
        try:
            # 購入済みチェックが入ったアイテムを探す
            item_ids = [
                key.split("_")[1]
                for key in request.POST.keys()
                if key.startswith("purchased_") and request.POST.get(key) == "on"
            ]

            if not item_ids:
                return JsonResponse({"success": False, "message": "購入済みアイテムが選択されていません。"})

            for item_id in item_ids:
                # 個別の購入数量と購入日を取得
                purchased_quantity = request.POST.get(f"purchased_quantity_{item_id}")
                purchased_date = request.POST.get(f"purchased_date_{item_id}")

                if not purchased_quantity or not purchased_date:
                    # 必要なデータがない場合はスキップ
                    continue

                # アイテムを取得して在庫を更新
                item = get_object_or_404(Item, id=item_id, user=request.user)
                purchased_quantity = int(purchased_quantity)

                # 在庫更新
                item.stock_quantity += purchased_quantity
                item.save()

                # 購入履歴を作成
                PurchaseHistory.objects.create(
                    item=item,
                    purchased_quantity=purchased_quantity,
                    purchased_date=purchased_date,
                )

                # 在庫が最低在庫数を上回った場合の処理
                if item.stock_quantity >= item.stock_min_threshold:
                    PurchaseItem.objects.filter(item=item).delete()

            # messages.success(request, "購入済みのアイテムが更新されました。")
            return redirect("shopping_list")

        except Exception as e:
            messages.error(request, f"エラーが発生しました: {e}")
            return redirect("shopping_list")

    messages.error(request, "無効なリクエストです。")
    return redirect("shopping_list")





def mark_item_as_purchased(request, purchase_item_id):
    try:
        purchase_item = get_object_or_404(PurchaseItem, id=purchase_item_id, item__user=request.user)
        purchased_quantity = int(request.POST.get("purchased_quantity", 0))
        if purchased_quantity <= 0:
            raise ValueError("購入数量は正の値である必要があります。")
    except (ValueError, KeyError) as e:
        return JsonResponse({"success": False, "error": f"無効なデータ: {e}"})

    try:
        # 履歴に保存
        PurchaseHistory.objects.create(
            item=purchase_item.item,
            purchased_date=now().date(),
            purchased_quantity=purchased_quantity
        )
        # 在庫を更新
        purchase_item.item.stock_quantity += purchased_quantity
        purchase_item.item.save()

        # 購入頻度を更新
        purchase_item.item.update_purchase_frequency()

        # 購入予定を削除
        purchase_item.delete()

        return JsonResponse({"success": True, "message": "購入履歴に追加されました。"})

    except Exception as e:
        return JsonResponse({"success": False, "error": f"エラーが発生しました: {e}"})

def add_store_item_reference(request, item_id, store_id):
    item = get_object_or_404(Item, id=item_id)
    store = get_object_or_404(Store, id=store_id)
    price = request.POST.get("price")
    price_per_unit = request.POST.get("price_per_unit")

    reference = StoreItemReference(
        item=item,
        store=store,
        price=price,
        price_per_unit=price_per_unit,
    )

    try:
        reference.full_clean()  # バリデーションを適用
        reference.save()
        return JsonResponse({"success": True, "message": "ストア情報が保存されました。"})
    except ValidationError as e:
        return JsonResponse({"success": False, "errors": e.messages})