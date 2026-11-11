import logging

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class TestRunner(DiscoverRunner):
    """
    Runs tests against an in-memory cache so they never read, write or flush the dev Redis,
    uses plain static file storage (no collectstatic needed),
    and hides the per-request 4xx warnings that tests trigger on purpose.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._settings_override = override_settings(
            CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
            # The manifest storage needs collectstatic to have run; tests don't need hashed files.
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
            },
        )
        self._settings_override.enable()
        logging.getLogger('django.request').setLevel(logging.ERROR)

    def teardown_test_environment(self, **kwargs):
        self._settings_override.disable()
        super().teardown_test_environment(**kwargs)
