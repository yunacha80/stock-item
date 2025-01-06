
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction,models
from django.db.models import Min,F,Max,Q
from django.http import JsonResponse
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
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from .models import Item,ItemCategory,PurchaseHistory,Store,StoreTravelTime,StoreItemReference,PurchaseItem
from .forms import CustomPasswordChangeForm,ItemForm, ItemCategoryForm,PurchaseHistoryForm,StoreForm,StoreTravelTimeFormSet,StoreTravelTimeForm,StoreItemReferenceForm
from django.utils import timezone
from django.utils.timezone import now
from django.http import Http404
import json
from itertools import permutations
from django.core.exceptions import ValidationError
from collections import defaultdict



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

    # 全アイテムとカテゴリを取得
    items = Item.objects.filter(user=user)
    categories = ItemCategory.objects.filter(user=user).order_by('display_order')

    # カテゴリ選択
    selected_category = request.GET.get('category', 'all')
    if selected_category == 'all':
        displayed_items = items
    else:
        displayed_items = items.filter(category__name=selected_category)

    # 最終購入日を取得
    item_data = []
    for item in displayed_items:
        last_purchase = item.purchase_histories.order_by('-purchased_date').first()
        item_data.append({
            'item': item,
            'last_purchase_date': last_purchase.purchased_date if last_purchase else None,
        })

    # 買い物リストに追加されているアイテムのIDを取得
    shopping_list_items = PurchaseHistory.objects.filter(item__in=items).values_list('item_id', flat=True).distinct()
    print(list(shopping_list_items))  # デバッグ用


    return render(request, 'item_list.html', {
        'categories': categories,
        'selected_category': selected_category,
        'displayed_items': displayed_items,
        'item_data': item_data,
        'shopping_list_items': list(shopping_list_items), 
    })





@login_required
def add_item(request):
    stores = Store.objects.all()  # 登録済みの全店舗を取得
    store_forms = []

    # 店舗ごとにフォームを作成
    for store in stores:
        store_item_reference = StoreItemReference(store=store)  # store を設定したインスタンス
        form = StoreItemReferenceForm(instance=store_item_reference, prefix=f"store_{store.id}")
        store_forms.append(form)

    if request.method == 'POST':
        item_form = ItemForm(request.POST)
        store_forms = [
            StoreItemReferenceForm(
                request.POST,
                instance=StoreItemReference(store=store),
                prefix=f"store_{store.id}"
            )
            for store in stores
        ]

        if item_form.is_valid() and all(form.is_valid() for form in store_forms):
            # アイテムを保存
            item = item_form.save(commit=False)
            item.user = request.user
            item.save()

            # 購入履歴を保存（購入日が入力されている場合）
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

            # 各店舗情報を保存
            for form in store_forms:
                store_reference = form.save(commit=False)
                store_reference.item = item

                # チェックボックスの処理
                price_unknown = form.cleaned_data.get('price_unknown', False)
                no_price = form.cleaned_data.get('no_price', False)
                if price_unknown or no_price:
                    store_reference.price = None
                    store_reference.price_per_unit = None

                store_reference.save()

            return redirect('item_list')  # アイテム一覧ページにリダイレクト
        else:
            print("バリデーションエラー発生")
            print(item_form.errors)
            for form in store_forms:
                print(form.errors)

    else:
        item_form = ItemForm()

    return render(request, 'add_item.html', {
        'item_form': item_form,
        'store_forms': store_forms,
    })



@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    stores = Store.objects.all()
    store_forms = []

    # 最新の購入履歴を取得
    last_purchase = PurchaseHistory.objects.filter(item=item).order_by('-purchased_date').first()
    last_purchase_date = last_purchase.purchased_date if last_purchase else None

    # 店舗ごとにフォームを作成
    for store in stores:
        store_item_reference = StoreItemReference.objects.filter(store=store, item=item).first()
        form = StoreItemReferenceForm(instance=store_item_reference, prefix=f"store_{store.id}")
        store_forms.append(form)

    if request.method == 'POST':
        item_form = ItemForm(request.POST, instance=item)
        store_forms = [
            StoreItemReferenceForm(
                request.POST,
                instance=StoreItemReference.objects.filter(store=store, item=item).first(),
                prefix=f"store_{store.id}"
            )
            for store in stores
        ]

        if item_form.is_valid() and all(form.is_valid() for form in store_forms):
            # アイテムを保存
            updated_item = item_form.save(commit=False)
            updated_item.user = request.user
            updated_item.save()

            # 購入履歴を保存または更新（最終購入日が入力されている場合のみ）
            last_purchase_date = item_form.cleaned_data.get('last_purchase_date')
            if last_purchase_date:
                purchase_histories = PurchaseHistory.objects.filter(
                    item=updated_item,
                    purchased_date=last_purchase_date
                )

                if purchase_histories.exists():
                    purchase_history = purchase_histories.first()
                    purchase_history.purchased_quantity += updated_item.stock_quantity
                    purchase_history.save()

                # 重複する履歴を削除
                purchase_histories.exclude(id=purchase_history.id).delete()
            else:
                # 新しい履歴を作成
                PurchaseHistory.objects.create(
                    item=updated_item,
                    purchased_date=last_purchase_date,
                    purchased_quantity=updated_item.stock_quantity
                )


            # アイテムの購入頻度を計算
            purchase_histories = PurchaseHistory.objects.filter(item=updated_item).order_by('purchased_date')
            if purchase_histories.count() > 1:
                intervals = [
                    (purchase_histories[i].purchased_date - purchase_histories[i - 1].purchased_date).days
                    for i in range(1, purchase_histories.count())
                ]
                purchase_frequency = sum(intervals) // len(intervals)
                updated_item.purchase_frequency = purchase_frequency
                updated_item.save()

            # 各店舗情報を保存
            for form in store_forms:
                store_reference = form.save(commit=False)
                store_reference.item = updated_item

                # チェックボックスの処理
                price_unknown = form.cleaned_data.get('price_unknown', False)
                no_price = form.cleaned_data.get('no_price', False)

                if price_unknown or no_price:
                    store_reference.price = None
                    store_reference.price_per_unit = None

                store_reference.save()

            return redirect('item_list')  # アイテム一覧ページにリダイレクト
        else:
            print("バリデーションエラー発生")
            print(item_form.errors)
            for form in store_forms:
                print(form.errors)

    else:
        item_form = ItemForm(instance=item, initial={'last_purchase_date': last_purchase_date})

    return render(request, 'edit_item.html', {
        'item_form': item_form,
        'store_forms': store_forms,
        'item': item,
    })




def item_delete(request, item_id):
    # ユーザーが所有するアイテムを取得
    item = get_object_or_404(Item, id=item_id, user=request.user)

    if request.method == "POST":  # POST リクエストを受けた場合
        print(f"Deleting item: {item.id}")  # デバッグ用出力
        item.delete()  # アイテムを削除
        return redirect('item_list')  # 削除後のリダイレクト

    # GET リクエストの場合、削除確認ページを表示
    return render(request, 'item_confirm_delete.html', {'item': item})

# def item_detail(request, item_id):
#     item = Item.objects.get(id=item_id)
#     price_references = StoreItemReference.objects.filter(item=item)

#     if request.method == 'POST':
#         form = StoreItemReferenceForm(request.POST)
#         if form.is_valid():
#             price_ref = form.save(commit=False)
#             price_ref.item = item
#             price_ref.save()
#             return redirect('item_detail', item_id=item.id)
#     else:
#         form = StoreItemReferenceForm()

#     return render(request, 'items/item_detail.html', {
#         'item': item,
#         'price_references': price_references,
#         'form': form,
#     })


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
            return redirect('category_list')
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
            return redirect('category_list')
    else:
        form = ItemCategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form})


def category_delete(request, category_id):
    category = get_object_or_404(ItemCategory, id=category_id)
    if request.method == "POST":
        category.delete()
        return redirect('category_list')
    return render(request, 'category_confirm_delete.html', {'category': category})



# 購入履歴
# 購入履歴をグループ化してデバッグ出力
def purchase_history_list(request):
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')

    # 購入日でグループ化
    grouped_histories = defaultdict(list)
    for history in histories:
        grouped_histories[history.purchased_date].append(history)

    # デバッグ出力
    for date, items in grouped_histories.items():
        print(f"購入日: {date}, アイテム: {[item.item.name for item in items]}")

    return render(request, 'purchase_history_list.html', {
        'grouped_histories': grouped_histories,
    })



# 購入履歴検索
@login_required
def purchase_history_Search(request):
    # 現在のユーザーに関連する購入履歴を取得
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')

    # フォームを現在のユーザー情報とともに初期化
    form = PurchaseHistoryFilterForm(request.GET or None, user=request.user)

    # フォームが有効であれば絞り込みを実行
    if form.is_valid():
        item = form.cleaned_data.get('item')
        if item:
            histories = histories.filter(item=item)

    return render(request, 'purchase_history_list.html', {
        'histories': histories,
        'form': form,
    })




# 店舗追加
# def store_add(request):
#     if request.method == 'POST':
#         form = StoreForm(request.POST)
#         formset = StoreTravelTimeFormSet(request.POST)
#         if form.is_valid() and formset.is_valid():
#             store = form.save(commit=False)
#             store.user = request.user  # 現在のログインユーザーを関連付ける
#             store.save()

#             store_travel_times = formset.save(commit=False)
#             for travel in store_travel_times:
#                 travel.store_from = store
#                 travel.save()
#             return redirect('store_list')  # 店舗一覧ページにリダイレクト（適宜URLを設定）
#     else:
#         form = StoreForm()
#         formset = StoreTravelTimeFormSet()
#     return render(request, 'store_add.html', {'form': form, 'formset': formset})

# 店舗一覧
def store_list(request):
    stores = Store.objects.filter(user=request.user)
    if not stores.exists():
        messages.info(request, "登録された店舗がありません。")    
    return render(request, 'store_list.html', {'stores': stores})


# def store_edit(request, pk):
#     store = get_object_or_404(Store, pk=pk, user=request.user)
#     if request.method == 'POST':
#         form = StoreForm(request.POST, instance=store)
#         formset = StoreTravelTimeFormSet(request.POST, instance=store)
#         if form.is_valid() and formset.is_valid():
#             form.save()
#             store_travel_times = formset.save(commit=False)
#             for travel in store_travel_times:
#                 travel.store_from = store
#                 travel.save()
#             messages.success(request, "店舗情報が更新されました。")
#             return redirect('store_list')
#         else:
#             messages.error(request, "フォームにエラーがあります。")
#     else:
#         form = StoreForm(instance=store)
#         formset = StoreTravelTimeFormSet(instance=store)
#     return render(request, 'store_edit.html', {'form': form, 'formset': formset})


def store_delete(request, store_id):
    store = get_object_or_404(Store, id=store_id, user=request.user)
    if request.method == "POST":
        store.delete()
        messages.success(request, "店舗が削除されました。")
        return redirect('store_list')  # URL名を使用
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
    stores = Store.objects.filter(user=request.user)  # 登録済み店舗の取得

    if request.method == 'POST':
        store_form = StoreForm(request.POST)

        if store_form.is_valid():
            try:
                with transaction.atomic():  # トランザクションを開始
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
                    return redirect('store_list')

            except Exception as e:
                print(f"Error: {e}")
                messages.error(request, "店舗の追加中にエラーが発生しました。")
            
    else:
        store_form = StoreForm()

    return render(request, 'store_add.html', {'store_form': store_form, 'stores': stores})

# 店舗編集
def store_edit(request, pk):
    store = Store.objects.get(pk=pk, user=request.user)
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        formset = StoreTravelTimeFormSet(request.POST, instance=store)
        if form.is_valid() and formset.is_valid():
            form.save()

            store_travel_times = formset.save(commit=False)
            for travel in store_travel_times:
                travel.store1 = store  # 出発店舗を設定
                travel.save()

            messages.success(request, "店舗情報と移動時間が更新されました。")
            return redirect('store_list')
    else:
        form = StoreForm(instance=store)
        formset = StoreTravelTimeFormSet(instance=store)

    return render(request, 'store_edit.html', {'form': form, 'formset': formset})

@login_required
def settings_view(request):
    """
    設定画面ビュー
    """
    # 現在の初期値（既存の stock_min_threshold のうち一つの値を取得、なければデフォルトを 1 に設定）
    default_stock = Item.objects.filter(user=request.user).first()
    default_stock_value = default_stock.stock_min_threshold if default_stock else 1
    
    stores = Store.objects.all()  # Storeモデルの全店舗を取得
    
    # カテゴリデータを取得
    categories = ItemCategory.objects.filter(user=request.user).order_by('display_order')

    if request.method == "POST":
        # 初期値設定処理
        new_value = request.POST.get("default_stock", None)
        if new_value is not None:
            try:
                new_value = int(new_value)
                if new_value >= 0:
                    # 新しい初期値を全アイテムの既定値として設定
                    Item.objects.filter(user=request.user).update(stock_min_threshold=new_value)
                    default_stock_value = new_value  # 現在の初期値を更新
            except ValueError:
                pass  # 無効な値は無視

        # カテゴリ追加処理
        if "add_category" in request.POST:
            category_name = request.POST.get("category_name", "").strip()
            if category_name:
                ItemCategory.objects.create(user=request.user, name=category_name)

    return render(request, "settings.html", {
        "default_stock": default_stock_value,
        "categories": categories,
        'stores': stores
    })




@login_required
@require_POST
def update_stock_min_threshold(request):
    """在庫最低値のデフォルト値を更新"""
    new_threshold = request.POST.get("stock_min_threshold")
    try:
        new_threshold = int(new_threshold)
        # デフォルト値を保存（例: ユーザープロファイルに保存する場合）
        request.user.profile.default_stock_min_threshold = new_threshold
        request.user.profile.save()
        messages.success(request, f"在庫最低値を {new_threshold} に更新しました。")
    except ValueError:
        messages.error(request, "無効な数値です。")
    return redirect("settings")

# def shopping_list_view(request):
#     """
#     買い物リストを表示するビュー
#     """
#     shopping_items = ShoppingList.objects.filter(item__user=request.user)
#     # 追加のデバッグ出力（開発用）
#     for shopping_item in shopping_items:
#         print(f"アイテム名: {shopping_item.item.name}, 現在在庫数: {shopping_item.item.stock_quantity}, 最低在庫数: {shopping_item.item.stock_min_threshold}")

#     # 購入予定数を最低在庫値に基づいて調整
#     for item in shopping_items:
#         if item.quantity_to_buy < item.item.stock_min_threshold - item.item.stock_quantity:
#             item.quantity_to_buy = item.item.stock_min_threshold - item.item.stock_quantity

#     return render(request, 'shopping_list.html', {'shopping_items': shopping_items})

# @require_POST
# def update_quantity(request, shopping_list_id):
#     """
#     購入予定数を増減する
#     """
#     shopping_item = get_object_or_404(ShoppingList, id=shopping_list_id)
#     action = request.POST.get('action')

#     if action == 'increment':
#         shopping_item.quantity_to_buy += 1
#     elif action == 'decrement' and shopping_item.quantity_to_buy > 0:
#         shopping_item.quantity_to_buy -= 1

#     shopping_item.save()
#     return JsonResponse({'quantity_to_buy': shopping_item.quantity_to_buy})



# @require_POST
# def delete_from_list(request, shopping_list_id):
#     """
#     買い物リストからアイテムを削除する
#     """
#     shopping_item = get_object_or_404(ShoppingList, id=shopping_list_id)
#     shopping_item.delete()
#     return JsonResponse({'success': True})

# @require_POST
# def mark_as_purchased(request, shopping_list_id):
#     """
#     購入済みとしてマークし、購入履歴に保存。
#     在庫数が最低在庫数を超えた場合、買い物リストから削除。
#     """
#     shopping_item = get_object_or_404(ShoppingList, id=shopping_list_id)
#     purchased_quantity = int(request.POST.get('purchased_quantity', 0))
#     purchased_date = request.POST.get('purchased_date')

#     # 入力値の検証
#     if purchased_quantity <= 0 or not purchased_date:
#         return JsonResponse({'success': False, 'error': '購入数または購入日が無効です。'})

#     # 購入履歴を保存
#     PurchaseHistory.objects.create(
#         item=shopping_item.item,
#         purchased_date=purchased_date,
#         purchased_quantity=purchased_quantity
#     )

#     # 在庫数を更新
#     initial_stock = shopping_item.item.stock_quantity  # デバッグ用
#     shopping_item.item.stock_quantity += purchased_quantity
#     shopping_item.item.save()

#     # デバッグログ
#     print(f"Item ID: {shopping_item.item.id}, Initial Stock: {initial_stock}, Purchased: {purchased_quantity}, Updated Stock: {shopping_item.item.stock_quantity}, Min Threshold: {shopping_item.item.stock_min_threshold}")

#     # 在庫が最低値を満たした場合、リストから削除
#     if shopping_item.item.stock_quantity >= shopping_item.item.stock_min_threshold:
#         shopping_item.delete()
#         return JsonResponse({'success': True, 'removed': True})

#     # 在庫がまだ不足している場合
#     return JsonResponse({'success': True, 'removed': False})


# @require_POST
# def add_item_to_shopping_list(request, item_id):
#     """
#     ユーザーが手動でアイテムを買い物リストに追加する
#     """
#     item = get_object_or_404(Item, id=item_id)

#     # アイテムがすでにリストにない場合に追加
#     if not ShoppingList.objects.filter(user=request.user, item=item).exists():
#         ShoppingList.objects.create(user=request.user, item=item, quantity_to_buy=1)

#     return JsonResponse({'success': True})
# def generate_shopping_suggestions(items, request):
#     """
#     買い回り提案の生成。
#     """
#     # 最安値提案
#     price_suggestion = generate_price_suggestion(items)

#     # 最短時間提案
#     time_suggestion = generate_time_suggestion(items, request)

#     # 低価格 + 短時間提案
#     combined_suggestion = generate_combined_suggestion(items, request)

#     return [price_suggestion, time_suggestion, combined_suggestion]





def reset_hidden_items(request):
    """
    非表示リストをリセットして全アイテムを再表示する
    """
    if request.method == "POST":
        request.session["hidden_items"] = []
        messages.success(request, "非表示リストがリセットされました。")
    return redirect("shopping_list")



# def shopping_suggestions_view(request):
#     """
#     買い回り提案画面。
#     """
#     # ユーザーが選択したアイテムを取得
#     item_ids = request.GET.getlist("item_ids", [])
#     items = Item.objects.filter(id__in=item_ids, user=request.user)

#     if not items:
#         return render(request, "shopping_suggestions.html", {
#             "error": "選択されたアイテムがありません。",
#         })

#     # 提案ロジックを適用
#     suggestions = generate_shopping_suggestions(items)

#     return render(request, "shopping_suggestions.html", {
#         "items": items,
#         "suggestions": suggestions,
#     })



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




def calculate_lowest_price_route(purchase_items):
    results = {}
    missing_items = []
    total_price = 0
    unit_total_price = 0
    store_details = {}
    route = []
    travel_times = {}

    # 店舗間の移動時間を準備
    stores = Store.objects.all()
    for store1 in stores:
        for store2 in stores:
            if store1 != store2:
                travel_times[(store1, store2)] = StoreTravelTime.objects.filter(
                    store1=store1, store2=store2
                ).first().travel_time_min

    for item in purchase_items:
        references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)

        if not references.exists():
            missing_items.append(item.name)
            continue

        best_reference = min(references, key=lambda ref: ref.price / ref.price_per_unit)
        store = best_reference.store
        unit_price = best_reference.price / best_reference.price_per_unit
        item_total_price = best_reference.price

        results[item.name] = {
            'store': store.name,
            'unit_price': unit_price,
            'price': item_total_price,
            'quantity': item.planned_purchase_quantity,
        }

        if store not in route:
            route.append(store)

        # 店舗ごとの商品詳細
        if store.name not in store_details:
            store_details[store.name] = []
        store_details[store.name].append({
            'name': item.name,
            'quantity': item.planned_purchase_quantity,
            'unit_price': unit_price,
        })

        total_price += item_total_price
        unit_total_price += unit_price

    # ルートを整形
    cleaned_route = clean_route(route)

    # デバッグ用出力
    print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
    print(f"DEBUG: Travel Times: {travel_times}")

    # 移動時間を計算
    total_travel_time = calculate_travel_time(cleaned_route, travel_times)

    # デバッグ用出力
    print(f"DEBUG: Total Travel Time: {total_travel_time}")

    return results, total_travel_time, missing_items, total_price, unit_total_price, store_details




def calculate_shortest_time_route(purchase_items):
    """
    最短時間提案の計算。
    """
    results = {}
    route = []
    missing_items = []
    total_price = 0
    unit_total_price = 0
    store_details = {}
    travel_times = {}

    # 店舗間の移動時間を準備
    stores = Store.objects.all()
    for store1 in stores:
        for store2 in stores:
            if store1 != store2:
                travel_time = StoreTravelTime.objects.filter(store1=store1, store2=store2).first()
                if travel_time:
                    travel_times[(store1, store2)] = travel_time.travel_time_min

    # 商品ごとに最短時間の店舗を選定
    for item in purchase_items:
        references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)

        if not references.exists():
            missing_items.append(item.name)
            continue

        valid_stores = [ref.store for ref in references]
        best_store = min(valid_stores, key=lambda store: store.travel_time_home_min)

        best_reference = references.filter(store=best_store).first()
        item_price = best_reference.price or 0
        unit_price = best_reference.price / best_reference.price_per_unit if best_reference.price_per_unit else 0

        results[item.name] = {
            'store': best_store.name,
            'travel_time': best_store.travel_time_home_min,
            'price': item_price,
            'quantity': item.planned_purchase_quantity,
        }

        if best_store not in route:
            route.append(best_store)

        # 店舗ごとの商品詳細
        if best_store.name not in store_details:
            store_details[best_store.name] = []
        store_details[best_store.name].append({
            'name': item.name,
            'quantity': item.planned_purchase_quantity,
            'unit_price': unit_price,
        })

        total_price += item_price
        unit_total_price += unit_price

    # 移動時間の計算
    cleaned_route = clean_route(route)
    total_travel_time = calculate_travel_time(cleaned_route, travel_times)

    # デバッグ用出力
    print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
    print(f"DEBUG: Travel Times: {travel_times}")
    print(f"DEBUG: Total Travel Time: {total_travel_time}")

    return results, total_travel_time, missing_items, total_price, unit_total_price, store_details




def calculate_best_balance_route(purchase_items):
    balance_results = {}
    combined_total_price = 0
    combined_unit_total = 0
    store_details = {}
    route = []
    travel_times = {}

    # 店舗間の移動時間を準備
    stores = Store.objects.all()
    for store1 in stores:
        for store2 in stores:
            if store1 != store2:
                travel_time = StoreTravelTime.objects.filter(store1=store1, store2=store2).first()
                if travel_time:
                    travel_times[(store1, store2)] = travel_time.travel_time_min

    # 各商品の最適店舗を選択しスコアを計算
    for item in purchase_items:
        references = StoreItemReference.objects.filter(item=item).exclude(price=None, price_per_unit=None)

        if not references.exists():
            continue

        # スコア計算 (価格と移動時間のバランス)
        best_reference = min(references, key=lambda ref: 0.6 * ref.price + 0.4 * ref.store.travel_time_home_min)
        best_store = best_reference.store
        route.append(best_store)

        item_price = best_reference.price or 0
        unit_price = best_reference.price / best_reference.price_per_unit if best_reference.price_per_unit else 0

        combined_total_price += item_price
        combined_unit_total += unit_price

        balance_results[item.name] = {
            'store': best_store.name,
            'score': 0.6 * item_price + 0.4 * best_store.travel_time_home_min,
            'price': item_price,
            'quantity': item.planned_purchase_quantity,
        }

        # 店舗ごとの商品詳細を構築
        if best_store.name not in store_details:
            store_details[best_store.name] = []
        store_details[best_store.name].append({
            'name': item.name,
            'quantity': item.planned_purchase_quantity,
            'unit_price': unit_price,
        })

    # ルート内の重複店舗を削除
    cleaned_route = clean_route(route)

    # 総移動時間を計算
    total_travel_time = calculate_travel_time(cleaned_route, travel_times)

    # デバッグ用出力
    print(f"DEBUG: Cleaned Route: {[store.name for store in cleaned_route]}")
    print(f"DEBUG: Total Travel Time: {total_travel_time}")

    # 未購入品リストは未処理アイテムから生成
    combined_missing = [item.name for item in purchase_items if item.name not in balance_results]

    return balance_results, combined_missing, combined_total_price, combined_unit_total, store_details, total_travel_time




@login_required
def shopping_list_view(request):
    """
    買い物リストの表示、購入済み処理、提案生成を管理。
    """
    items = Item.objects.filter(
        user=request.user, stock_quantity__lt=models.F('stock_min_threshold')
    ).annotate(
        planned_purchase_quantity=models.F('stock_min_threshold') - models.F('stock_quantity')
    )

    suggestions = []
    feedback_messages = []

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "suggest":
            # 提案生成処理
            try:
                # 最安値提案
                price_suggestion, price_travel_time, price_missing, price_total, price_unit_total, price_store_details = calculate_lowest_price_route(items)

                # 最短時間提案
                time_suggestion, time_travel_time, time_missing, time_total, time_unit_total, time_store_details = calculate_shortest_time_route(items)

                # 低価格＋短時間提案
                combined_suggestion, combined_missing, combined_total_price, combined_unit_total, combined_store_details, combined_total_time = calculate_best_balance_route(items)

                # 提案リストを作成
                suggestions = [
                    {
                        "type": "最安値",
                        "details": price_suggestion,
                        "total_price": price_total,
                        "unit_total_price": price_unit_total,
                        "route": clean_route([data["store"] for data in price_suggestion.values()]),
                        "total_time": price_travel_time,
                        "store_details": price_store_details,
                        "missing_items": price_missing,
                    },
                    {
                        "type": "最短時間",
                        "details": time_suggestion,
                        "total_price": time_total,
                        "unit_total_price": time_unit_total,
                        "route": clean_route([data["store"] for data in time_suggestion.values()]),
                        "total_time": time_travel_time,
                        "store_details": time_store_details,
                        "missing_items": time_missing,
                    },
                    {
                        "type": "低価格＋短時間",
                        "details": combined_suggestion,
                        "total_price": combined_total_price,
                        "unit_total_price": combined_unit_total,
                        "route": clean_route([data["store"] for data in combined_suggestion.values()]),
                        "total_time": combined_total_time,
                        "store_details": combined_store_details,
                        "missing_items": combined_missing,
                    },
                ]
            except Exception as e:
                feedback_messages.append(f"提案生成中にエラーが発生しました: {e}")
                print(f"DEBUG: Error: {e}")


    # 最新の買い物リストを取得
    purchase_items = PurchaseItem.objects.filter(item__user=request.user)

    return render(request, "shopping_list.html", {
        "items": items,
        "suggestions": suggestions,
        "messages": feedback_messages,
        "purchase_items": purchase_items,  # 買い物リストの最新アイテム
    })


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






# def suggest_stores(request):
#     """
#     買い回り提案を生成するビュー
#     """
#     if request.method == "POST":
#         item_ids = request.POST.getlist("item_ids")
#         items = Item.objects.filter(id__in=item_ids, user=request.user)

#         if not items:
#             return render(request, "shopping_list.html", {
#                 "error": "アイテムが選択されていません。",
#                 "items": items,
#             })

#         # アイテムとストアのマッピングを作成
#         item_store_map = {
#             item: StoreItemReference.objects.filter(item=item)
#             for item in items
#         }

#         # 提案を作成
#         price_suggestion = generate_price_suggestion(item_store_map)
#         time_suggestion = generate_time_suggestion(item_store_map)
#         combined_suggestion = generate_combined_suggestion(item_store_map)

#         # 提案を辞書形式で返す
#         suggestions = {
#             "最安値": price_suggestion,
#             "最短時間": time_suggestion,
#             "低価格＋短時間": combined_suggestion,
#         }

#         return render(request, "shopping_list.html", {
#             "items": items,
#             "suggestions": suggestions,
#         })

# def generate_price_suggestion(items):
#     """
#     最安値提案を生成。
#     :param items: アイテムクエリセット
#     :return: 提案内容
#     """
#     store_selection = {}
#     total_price = 0
#     unknown_items = []

#     for item in items:
#         # 単価計算で最安値を探す
#         cheapest_ref = StoreItemReference.objects.filter(
#             item=item, price__isnull=False, price_per_unit__isnull=False
#         ).annotate(
#             unit_price=models.F('price') / models.F('price_per_unit')
#         ).order_by('unit_price').first()

#         if cheapest_ref:
#             store = cheapest_ref.store
#             if store not in store_selection:
#                 store_selection[store] = []
#             store_selection[store].append({
#                 "item": item.name,
#                 "unit_price": cheapest_ref.unit_price,
#                 "price": cheapest_ref.price,
#             })
#             total_price += cheapest_ref.price
#         else:
#             unknown_items.append(item.name)

#     return {
#         "type": "最安値",
#         "route": [store.name for store in store_selection.keys()],
#         "total_price": total_price,
#         "details": store_selection,
#         "unknown_items": unknown_items,
#     }

# def generate_time_suggestion(items):
#     """
#     最短時間提案を生成。
#     :param items: アイテムクエリセット
#     :return: 提案内容
#     """
#     stores = list(Store.objects.filter(id__in=items.values_list('storeitemreference__store', flat=True).distinct()))
#     home_times = {store: store.travel_time_home_min for store in stores}
#     store_pairs = StoreTravelTime.objects.filter(store1__in=stores, store2__in=stores)

#     # 店舗間の移動時間辞書を構築
#     travel_times = {(pair.store1, pair.store2): pair.travel_time_min for pair in store_pairs}

#     # 全ルートの移動時間を計算
#     best_route = None
#     shortest_time = float('inf')

#     for route in permutations(stores):
#         total_time = 0
#         total_time += home_times[route[0]]  # 自宅→最初の店舗
#         for i in range(len(route) - 1):
#             total_time += travel_times.get((route[i], route[i + 1]), float('inf'))  # 店舗間の移動
#         total_time += home_times[route[-1]]  # 最後の店舗→自宅

#         if total_time < shortest_time:
#             shortest_time = total_time
#             best_route = route

#     return {
#         "type": "最短時間",
#         "route": [store.name for store in best_route],
#         "total_time": shortest_time,
#         "details": f"自宅→{'→'.join([store.name for store in best_route])}→自宅",
#     }

# def generate_combined_suggestion(items):
#     """
#     低価格＋短時間提案を生成。
#     """
#     # サンプルスコア計算（単価と時間の重み付け）
#     suggestions = []
#     for item in items:
#         for ref in StoreItemReference.objects.filter(item=item):
#             score = (ref.price or 0) * 0.7 + (ref.store.travel_time_home_min or 0) * 0.3
#             suggestions.append((ref.store.name, score))

#     sorted_suggestions = sorted(suggestions, key=lambda x: x[1])
#     route = [s[0] for s in sorted_suggestions[:3]]  # 上位3店舗

#     return {
#         "type": "低価格＋短時間",
#         "route": route,
#         "score": sum([s[1] for s in sorted_suggestions[:3]]),
#     }




def add_to_shopping_list(request):
    """
    在庫が足りないアイテムを自動で買い物リストに追加する
    """
    # 在庫が足りないアイテムを取得
    items_to_add = Item.objects.filter(user=request.user, stock_quantity__lt=models.F("stock_min_threshold"))
    
    for item in items_to_add:
        # ショッピングリストへの追加処理（実際のアプリケーションに応じて調整）
        # ここでは、アイテム名を表示して追加することを示しています。
        print(f"アイテム {item.name} を買い物リストに追加します。")
    
    return JsonResponse({"message": "在庫不足のアイテムが買い物リストに追加されました。"})

# @csrf_exempt
# def delete_item_from_list(request, item_id):
#     """
#     買い物リストからアイテムを削除
#     """
#     if request.method == "POST":
#         item = get_object_or_404(Item, id=item_id, user=request.user)
#         item.delete()  # アイテムを削除
#         return JsonResponse({"success": True})
#     return JsonResponse({"success": False, "error": "Invalid request method"})



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