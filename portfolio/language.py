from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.shortcuts import redirect
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from dashboard.models import DashboardPreferences


class AccountLocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        super().process_request(request)
        request.dashboard_preferences = (
            getattr(request.user, 'dashboardpreferences', None)
            if request.user.is_authenticated else None
        )
        if request.dashboard_preferences:
            code = request.dashboard_preferences.language
            translation.activate(code)
            request.LANGUAGE_CODE = code


@require_POST
def set_language(request):
    language = request.POST.get('language')
    target = request.POST.get('next', '/')
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        target = '/'
    url = urlsplit(target)
    params = [(key, value) for key, value in parse_qsl(url.query, keep_blank_values=True) if key != 'lang']
    response = redirect(urlunsplit(url._replace(query=urlencode(params))))
    if language in dict(settings.LANGUAGES):
        if request.user.is_authenticated:
            DashboardPreferences.objects.update_or_create(
                user=request.user, defaults={'language': language}
            )
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME, language, max_age=60 * 60 * 24 * 365, samesite='Lax',
            secure=request.is_secure(), httponly=True,
        )
    return response
