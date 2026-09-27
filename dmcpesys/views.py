from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Destination, State
from .serializers import DestinationSerializer, StateSerializer

class DestinationListView(APIView):
    """
    List all available destinations for the dropdown.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        destinations = Destination.objects.all().order_by('name')
        serializer = DestinationSerializer(destinations, many=True)
        return Response({
            'success': True,
            'destinations': serializer.data,
            'count': len(serializer.data)
        })


class IndianStateListView(APIView):
    """
    List all states of India for remittance management system / signup forms.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        states = State.objects.filter(
            Q(country__name__iexact="India") | Q(country__iso_code__iexact="IN")
        ).order_by('name')

        if not states.exists():
            states = State.objects.all().order_by('name')

        serializer = StateSerializer(states, many=True)
        return Response({
            'success': True,
            'states': serializer.data,
            'count': len(serializer.data)
        })

