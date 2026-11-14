from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='ai_dashboard'),
    path('dashboard/preferences/', views.preferences, name='dashboard_preferences'),
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
]
