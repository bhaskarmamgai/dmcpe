from django.utils.translation import gettext_lazy as _
from django.contrib.admin import SimpleListFilter
from bms.models.planned_payment.planned_payment import PlannedPayment


class PlannedPaymentToPayStatusFilter(SimpleListFilter):
    STATUSES = (
        (PlannedPayment.PENDING, "Pending"),
        (PlannedPayment.PAID, "Paid"),
        (PlannedPayment.CANCELLED, "Cancelled")
    )
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return self.STATUSES

    def queryset(self, request, queryset):
        if self.value() == PlannedPayment.CANCELLED:
            return queryset.filter(status=PlannedPayment.CANCELLED)
        elif self.value() == PlannedPayment.PAID:
            return queryset.filter(status=PlannedPayment.PAID)
        elif self.value() == PlannedPayment.PENDING:
            return queryset.filter(status=PlannedPayment.PENDING)
        else:
            return queryset


class PlannedPaymentToCollectStatusFilter(SimpleListFilter):
    STATUSES = (
        (PlannedPayment.PENDING, "Pending"),
        (PlannedPayment.COLLECTED, "Collected"),
        (PlannedPayment.CANCELLED, "Cancelled")
    )
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return self.STATUSES

    def queryset(self, request, queryset):
        if self.value() == PlannedPayment.CANCELLED:
            return queryset.filter(status=PlannedPayment.CANCELLED)
        elif self.value() == PlannedPayment.COLLECTED:
            return queryset.filter(status=PlannedPayment.COLLECTED)
        elif self.value() == PlannedPayment.PENDING:
            return queryset.filter(status=PlannedPayment.PENDING)
        else:
            return queryset
