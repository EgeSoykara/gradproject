from django.conf import settings
from django.db import models

LANGUAGES = [('tr', 'Türkçe'), ('en', 'English')]
PROFILES = [('conservative', 'Conservative'), ('balanced', 'Balanced'), ('aggressive', 'Aggressive')]
LEVELS = [('beginner', 'Beginner'), ('expert', 'Expert')]


class DashboardPreferences(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    language = models.CharField(max_length=2, choices=LANGUAGES, default='tr')
    currency = models.CharField(max_length=3, default='TRY')
    profile = models.CharField(max_length=12, choices=PROFILES, default='balanced')
    level = models.CharField(max_length=8, choices=LEVELS, default='beginner')
    monthly_contribution = models.DecimalField(max_digits=14, decimal_places=2, default=0)
