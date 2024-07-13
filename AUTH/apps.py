from django.apps import AppConfig
from django.conf import settings

from shutil import rmtree

import os


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'AUTH'

    def ready(self):
        if os.path.isdir(settings.TEMP_MEDIA_DIR):
            rmtree(settings.TEMP_MEDIA_DIR)
        os.mkdir(settings.TEMP_MEDIA_DIR)