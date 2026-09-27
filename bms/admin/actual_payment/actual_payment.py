from django.contrib import admin

from bms.models.actual_payment.actual_payment import ActualPayment


class ActualPaymentAdmin(admin.ModelAdmin):
    model = ActualPayment
    list_filter = ('member__account_manager', 'created_by', 'created_at')

    def get_queryset(self, request):
        return super(ActualPaymentAdmin, self).get_queryset(request).select_related('member', 'member__account_manager')


admin.site.register(ActualPayment, ActualPaymentAdmin)
