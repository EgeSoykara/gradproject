from django.contrib import admin
from django.urls import include, path

from portfolio.language import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('language/', set_language, name='set_language'),
    path('', include('dashboard.urls')),
    path('', include('portfolio.urls')),
]
