from rest_framework import serializers

from .models import LocationMaster, Currency, Area, Destination, Country, State, Category, Inclusion, TravelSupplyGroupEntities


# ============= Base Serializers =============

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['code', 'name', 'iso_code']


class StateSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = State
        fields = ['id', 'code', 'name', 'country']


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol']


class LocationSerializer(serializers.ModelSerializer):
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = LocationMaster
        fields = [
            'code', 'name', 'location_type', 'location_category',
            'is_island', 'latitude', 'longitude'
        ]

    def get_latitude(self, obj):
        if hasattr(obj, 'point') and obj.point:
            return float(obj.point.y)
        return None

    def get_longitude(self, obj):
        if hasattr(obj, 'point') and obj.point:
            return float(obj.point.x)
        return None


class DestinationSerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = Destination
        fields = ['id', 'name', 'country', ]



class AreaSerializer(serializers.ModelSerializer):
    destination = DestinationSerializer()

    class Meta:
        model = Area
        fields = ['id', 'name', 'destination']
