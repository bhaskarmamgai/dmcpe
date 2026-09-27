from django.apps import AppConfig


class BmsConfig(AppConfig):
    name = 'bms'
    verbose_name = 'BMS - Booking Management System'



    def ready(self):
        import bms.signals
