from django.apps import AppConfig


class UserAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'User_Auth'

    def ready(self):
        import User_Auth.signals  