from django.urls import include, path

from .router import router_farms
from .views import FarmMemberViewSet, FarmSetupView

urlpatterns = [
    path('setup/', FarmSetupView.as_view(), name='farm-setup'),
    # Members opera sobre la finca activa del usuario (sin farm_id en la URL).
    path('members/', FarmMemberViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='farm-members-list'),
    path('members/<int:pk>/', FarmMemberViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='farm-members-detail'),
    path('', include(router_farms.urls)),
]
