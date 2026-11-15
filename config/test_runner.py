import os
from unittest.mock import patch

from django.test.runner import DiscoverRunner


def blocked(*args, **kwargs):
    raise AssertionError('Network access is disabled during tests. Use a provider fixture.')


class OfflineTestRunner(DiscoverRunner):
    def run_tests(self, test_labels, **kwargs):
        with (
            patch.dict(os.environ, {'PORTFOLIO_AI_TEST_OFFLINE': '1'}),
            patch('requests.sessions.Session.send', blocked),
            patch('curl_cffi.requests.Session.request', blocked),
            patch('socket.getaddrinfo', blocked),
            patch('socket.socket.connect', blocked),
            patch('socket.socket.connect_ex', blocked),
        ):
            return super().run_tests(test_labels, **kwargs)
