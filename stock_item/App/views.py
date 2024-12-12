
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction,models
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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
from .models import Item,ItemCategory,PurchaseHistory,Store,StoreTravelTime,StoreItemReference
from .forms import CustomPasswordChangeForm,ItemForm, ItemCategoryForm,PurchaseHistoryForm,StoreForm,StoreTravelTimeFormSet,StoreTravelTimeForm,StoreItemReferenceForm
from django.utils import timezone
from django.utils.timezone import now
import json



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
            return redirect("home")
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
    items = Item.objects.all()  
    return render(request, 'item_list.html', {'items': items})






@login_required
def add_item(request):
    stores = Store.objects.all()  # 登録済みの全店舗を取得
    store_forms = []

    # 店舗ごとにフォームを作成し、インスタンスを明示的に設定
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
            item = item_form.save(commit=False)  # commit=Falseで一時的に保存
            item.user = request.user  # 現在のユーザーを設定
            item.save()  # ユーザー情報を設定した後に保存

            # 購入履歴を保存
            last_purchase_date = item_form.cleaned_data['last_purchase_date']
            purchase_history = PurchaseHistory(item=item, purchased_date=last_purchase_date, purchased_quantity=item.stock_quantity)
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
                price_unknown = form.cleaned_data.get('price_unknown')
                no_price = form.cleaned_data.get('no_price')
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
    item = get_object_or_404(Item, id=item_id)  # 編集するアイテムを取得
    stores = Store.objects.all()  # 登録済みの全店舗を取得
    store_forms = []

    # 店舗ごとにフォームを作成し、インスタンスを明示的に設定
    for store in stores:
        store_item_reference = StoreItemReference.objects.filter(store=store, item=item).first()
        form = StoreItemReferenceForm(instance=store_item_reference, prefix=f"store_{store.id}")
        store_forms.append(form)

    if request.method == 'POST':
        item_form = ItemForm(request.POST, instance=item)  # 既存のアイテムデータを使用
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
            updated_item.user = request.user  # ユーザー情報を設定（必要であれば）
            updated_item.save()

            # 購入履歴を保存または更新
            last_purchase_date = item_form.cleaned_data['last_purchase_date']
            purchase_history, created = PurchaseHistory.objects.get_or_create(
                item=updated_item,
                purchased_date=last_purchase_date,
                defaults={'purchased_quantity': updated_item.stock_quantity}
            )
            if not created:
                purchase_history.purchased_quantity = updated_item.stock_quantity
                purchase_history.save()

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
                price_unknown = form.cleaned_data.get('price_unknown')
                no_price = form.cleaned_data.get('no_price')
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
        item_form = ItemForm(instance=item)  # 既存のアイテムデータを表示

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
    
@login_required
def category_add(request):
    if request.method == "POST":
        form = ItemCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user  # 現在のユーザーを設定
            category.save()
            return redirect('category_list')
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
def purchase_history_list(request):
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')
    return render(request, 'purchase_history_list.html', {'histories': histories})


# 購入履歴検索
def purchase_history_Search(request):
    # ユーザーに関連する購入履歴を取得
    histories = PurchaseHistory.objects.filter(item__user=request.user).order_by('-purchased_date')
    form = PurchaseHistoryFilterForm(request.GET)

    # アイテム名での絞り込み
    if form.is_valid() and form.cleaned_data['item']:
        histories = histories.filter(item=form.cleaned_data['item'])

    return render(request, 'items/purchase_history_list.html', {'histories': histories, 'form': form})


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



def shopping_list_view(request):
    """
    買い物リストを表示するビュー
    """
    # 在庫が足りないアイテムを取得（在庫が最低在庫数を下回ったアイテム）
    items = Item.objects.filter(user=request.user, stock_quantity__lt=models.F("stock_min_threshold"))
    
    return render(request, "shopping_list.html", {"items": items})


def update_stock_and_history(request, item_id):
    """
    購入済みのアイテムを更新し、購入履歴を保存
    """
    if request.method == "POST":
        # アイテムを取得
        item = get_object_or_404(Item, id=item_id, user=request.user)
        
        # 購入数と購入日を取得
        purchased_quantity = int(request.POST.get("purchased_quantity"))
        purchased_date = request.POST.get("purchased_date")
        
        # 在庫数を更新
        item.stock_quantity += purchased_quantity
        item.save()

        # 購入履歴を保存
        PurchaseHistory.objects.create(
            item=item,
            purchased_quantity=purchased_quantity,
            purchased_date=purchased_date
        )

        # 在庫が最低在庫数を超えた場合は買い物リストから削除
        if item.stock_quantity >= item.stock_min_threshold:
            return JsonResponse({"success": True, "removed": True})

        return JsonResponse({"success": True, "removed": False})


def suggest_stores(request):
    """
    アイテムの買い回り提案を行うビュー
    """
    # GETパラメータで送信されたアイテムのIDリストを取得
    item_ids = request.GET.getlist("item_ids")
    items = Item.objects.filter(id__in=item_ids, user=request.user)

    suggestions = []

    # アイテムごとの店舗提案を行う
    for item in items:
        stores = item.storeitemreference_set.all().order_by("price")[:3]  # 価格順で上位3件を取得
        suggestions.append({
            "item": item.name,
            "stores": [{"name": store.store.name, "price": store.price} for store in stores]
        })

    return JsonResponse({"suggestions": suggestions})


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