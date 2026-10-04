from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('holdings/', views.holdings, name='holdings'),
    path('transactions/', views.transactions, name='transactions'),
    path('transactions/new/', views.transaction_edit, name='transaction_new'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('compare/', views.compare, name='compare'),
    path('analysis/', views.analysis, name='analysis'),
    path('news/', views.news, name='news'),
    path('notes/', views.notes, name='notes'),
    path('notes/new/', views.note_edit, name='note_new'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
    path('settings/', views.settings_view, name='settings'),
    path('workspace/demo/', views.demo_load, name='demo_load'),
    path('workspace/switch/', views.portfolio_switch, name='portfolio_switch'),
    path('workspace/new/', views.portfolio_create, name='portfolio_create'),
    path('data/import/', views.market_import, name='market_import'),
]
