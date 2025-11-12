from django.apps import AppConfig


class PlatformSpecificsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_specifics'
