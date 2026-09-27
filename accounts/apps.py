from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    # https://simpleisbetterthancomplex.com/tutorial/2016/07/28/how-to-create-django-signals.html
    def ready(self):
        import accounts.signals
