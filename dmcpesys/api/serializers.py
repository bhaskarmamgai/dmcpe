from rest_framework import serializers
from ..models import Category, Inclusion, Destination, TravelSupplyGroupEntities, Currency


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'url', 'enabled']


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class CategorySerializerForBookingsDetails(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'url']


class InclusionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inclusion
        fields = ['id', 'name', 'enabled_icon', 'disable_icon']


class DestinationSerializerV2(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)

    class Meta:
        model = Destination
        fields = ['id', 'name', 'country_name', 'state_name']


class DestinationSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destination
        fields = ['id', 'name']


class TravelSupplyGroupEntitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelSupplyGroupEntities
        fields = ['id', 'name', 'code']


class TravelSupplyGroupEntitiesInternalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelSupplyGroupEntities
        fields = ['id', 'name', 'code', 'notes']
