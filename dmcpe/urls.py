"""
URL configuration for traventic_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from members.urls import urlpatterns as members_api_urls
from dmcpesys.urls import urlpatterns as dmcpesys_api_urls
from users.urls import urlpatterns as users_api_urls
from rms.urls import urlpatterns as rms_api_urls

from rest_framework_simplejwt.views import TokenRefreshView
from members.serializers import CustomTokenObtainPairView

urlpatterns = [
    path("grappelli/", include("grappelli.urls")),
    path("nested_admin/", include("nested_admin.urls")),
    path('admin/', admin.site.urls),
    path('users/auth/', include(users_api_urls)),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/', include(dmcpesys_api_urls + members_api_urls + rms_api_urls + users_api_urls)),
    path('api/v1/rms/', include('rms.urls')),
    path('bms/', include('bms.urls.admin')),
]

admin.site.site_header = 'DMCPE Administration'
admin.site.site_title = 'DMCPE Administration'
admin.site.index_title = 'DMCPE Administration'
