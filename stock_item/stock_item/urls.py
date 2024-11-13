"""
URL configuration for stock_item project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from App.views import PortfolioView, SignupView, LoginView,LogoutView,HomeView,PasswordChangeView, EmailChangeView, purchase_history_list
from App import views  




urlpatterns = [
    path("admin/", admin.site.urls),
    path('', PortfolioView.as_view(), name="portfolio"),
    path('signup/', SignupView.as_view(), name="signup"),
    path('login/', LoginView.as_view(), name="login"),
    path('home/', HomeView.as_view(), name="home"),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password_change/', PasswordChangeView.as_view(), name='password_change'),
    path('email_change/', EmailChangeView.as_view(), name='email_change'),
    path('items/add/', views.item_add, name='item_add'),
    path('items/', views.item_list, name='item_list'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<int:category_id>/', views.category_edit, name='category_edit'),
    path('categories/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    path('purchase_history/', views.purchase_history_list, name='purchase_history_list'),
    path('purchase_history/Search/', views.purchase_history_Search, name='purchase_history_Search'),
    path('stores/list/', views.store_list, name='store_list'),
    path('stores/edit/<int:store_id>/', views.store_edit, name='store_edit'),
    path('stores/delete/<int:store_id>/', views.store_delete, name='store_delete'),
    path('stores/add/', views.store_add, name='store_add'),
    path('stores/<int:pk>/edit/', views.store_edit, name='store_edit'),
]
