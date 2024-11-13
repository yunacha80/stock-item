
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction
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
from .models import Item, StoreItemReference,Category,PurchaseHistory,Store,StoreTravelTime
from .forms import CustomPasswordChangeForm,StoreItemReferenceFormSet,StoreItemReferenceForm, CategoryForm,PurchaseHistoryForm,StoreForm,StoreTravelTimeFormSet,StoreTravelTimeForm



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
    



def item_add(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        formset = StoreItemReferenceFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            item = form.save(commit=False)
            item.user = request.user  # 現在のログインユーザーを設定
            item.save()
            
            # フォームセットの各フォームにアイテムを関連付けて保存
            price_references = formset.save(commit=False)
            for price_reference in price_references:
                price_reference.item = item
                price_reference.save()
            
            return redirect('item_list')
    else:
        form = ItemForm()
        formset = StoreItemReferenceFormSet()
        
        
    return render(request, 'item_add.html', {'form': form, 'formset': formset})

def item_list(request):
    items = Item.objects.filter(user=request.user)
    return render(request, 'item_list.html', {'items': items})


def item_edit(request, item_id):
    item = get_object_or_404(Item, id=item_id, user=request.user)
    
    # アイテムに関連するすべての店舗を取得
    stores = Store.objects.all()  # すべての店舗を取得
    store_references = StoreItemReference.objects.filter(item=item)  # アイテムに関連する店舗ごとの価格情報

    # 店舗ごとの情報を辞書にまとめる
    store_reference_dict = {reference.store.id: reference for reference in store_references}

    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        formset = []

        # 各店舗に対してフォームを生成
        for store in stores:
            reference = store_reference_dict.get(store.id)
            formset.append(StoreItemReferenceForm(request.POST, instance=reference) if reference else StoreItemReferenceForm(request.POST))

        if form.is_valid() and all(f.is_valid() for f in formset):  # 各フォームを検証
            item = form.save(commit=False)
            item.user = request.user
            item.save()

            # 各店舗の価格情報を保存
            for store, reference_form in zip(stores, formset):
                reference = reference_form.save(commit=False)
                reference.item = item  # アイテムを関連付け
                reference.store = store  # 店舗を設定
                reference.save()

            return redirect('item_list')  # アイテム一覧へリダイレクト
    else:
        form = ItemForm(instance=item)
        formset = []

        # 各店舗に対してフォームを生成
        for store in stores:
            reference = store_reference_dict.get(store.id)
            formset.append(StoreItemReferenceForm(instance=reference) if reference else StoreItemReferenceForm())

    # stores_with_formsの作成（zipを1回使用）
    stores_with_forms = [
        {
            'store': store,
            'form': reference_form,
            'unit_price': reference_form.instance.price / reference_form.instance.unit_quantity if reference_form.instance.price and reference_form.instance.unit_quantity else None
        }
        for store, reference_form in zip(stores, formset)
    ]

    return render(request, 'item_form.html', {'form': form, 'stores_with_forms': stores_with_forms})


# アイテム削除
def item_delete(request, item_id):
    item = Item.objects.filter(user=request.user),get_object_or_404(Item, id=item_id)
    if request.method == "POST":
        item.delete()
        return redirect('item_list')
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
    categories = Category.objects.filter(user=request.user)
    if not categories:
        print("現在、カテゴリは存在しません。")  # デバッグ用の出力
    return render(request, 'category_list.html', {'categories': categories})
    
@login_required
def category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user  # 現在のユーザーを設定
            category.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'category_form.html', {'form': form})

# カテゴリ編集
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form})


def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
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
