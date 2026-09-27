from django.urls import path
from .views import DestinationListView, IndianStateListView

urlpatterns = [
    path('destinations/list/', DestinationListView.as_view(), name='destination-list'),
    path('states/india/', IndianStateListView.as_view(), name='indian-states-list'),
]

