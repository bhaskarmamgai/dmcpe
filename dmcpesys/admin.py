from django.contrib import admin
from .models import Country, Currency, State, Destination, Area, LocationMaster, TravelSupplyGroupEntities, Category, \
    RateOfExchange, BaseCurrencyCharge,Service,Bank


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'iso_code', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                    'created_by', 'updated_by')
    search_fields = ('name', 'iso_code')
    list_filter = ('is_active', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def code_display(self, obj):
        return obj.code  # Assuming CodeMixin provides code field

    code_display.short_description = 'Code'


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'symbol', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                    'created_by', 'updated_by')
    search_fields = ('name', 'symbol')
    list_filter = ('is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')


class StateInline(admin.TabularInline):
    model = State
    extra = 1
    fields = ('name', 'code')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'country', 'is_active', 'is_deleted', 'created_at',
                    'updated_at',
                    'created_by', 'updated_by')
    list_filter = ('country', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by')
    search_fields = ('name', 'country__name')
    ordering = ('country', 'name')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')


class DestinationInline(admin.TabularInline):
    model = Destination
    extra = 1
    fields = ('name', 'code')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'state', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                    'created_by', 'updated_by')
    list_filter = ('state__country', 'state', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by')
    search_fields = ('name', 'state__name', 'state__country__name')
    ordering = ('state__country', 'state', 'name')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')
    autocomplete_fields = ('state', 'country')


class AreaInline(admin.TabularInline):
    model = Area
    extra = 1
    fields = ('name', 'code')
    readonly_fields = ('code',)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'destination', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                    'created_by', 'updated_by', 'is_default')
    list_filter = ('destination', 'is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by', 'is_default')
    search_fields = ('name', 'destination__name', 'destination__state__name', 'destination__state__country__name')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')
    autocomplete_fields = ('destination',)


@admin.register(LocationMaster)
class LocationMasterAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'code', 'name', 'location_category', 'location_type',
        'country', 'state', 'destination', 'area',
        'destination', 'is_active', 'is_deleted', 'created_at', 'updated_at',
        'created_by', 'updated_by'
    )
    list_filter = ('location_type', 'country', 'state', 'destination', 'area', 'destination', 'is_active', 'is_deleted',
                   'created_at', 'updated_at',
                   'created_by', 'updated_by')
    search_fields = ('name', 'country__name', 'state__name', 'destination__name', 'area__name')
    ordering = ('country', 'state', 'destination', 'area', 'name')
    autocomplete_fields = ('destination', 'area', 'country', 'state')

    # Using collapse for spatial fields might improve UI
    fieldsets = (
        (None, {
            'fields': ('name', 'location_type', 'location_category')
        }),
        # ('Spatial Data', {
        #     # 'fields': ('point', 'polygon', 'multipolygon'),
        #     # 'fields': ('geom',),
        #     'classes': ('collapse',),
        # }),
        ('Hierarchy', {
            'fields': ('country', 'state', 'destination', 'area'),
        }),
        ('Code Info', {
            'fields': ('code',),
        }),
    )
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'updated_by')

    # Enable map widget for geometry fields
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 10,
        },
    }


@admin.register(TravelSupplyGroupEntities)
class TravelSupplyGroupEntitiesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_filter = ('is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    autocomplete_fields = ('country',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_filter = ('is_active', 'is_deleted', 'created_at', 'updated_at',
                   'created_by', 'updated_by')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(RateOfExchange)
class RateOfExchangeAdmin(admin.ModelAdmin):
    pass


@admin.register(BaseCurrencyCharge)
class BaseCurrencyChargeAdmin(admin.ModelAdmin):
    pass


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    pass

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    pass

admin.site.site_header = "Traventic Core Administration"
admin.site.site_title = "Traventic Core Admin Portal"
admin.site.index_title = "Welcome to Traventic Core"
