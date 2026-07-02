from django.urls import path

from .views import BirthView, ReproductiveEventViewSet, WeanView

urlpatterns = [
    path('', ReproductiveEventViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='repro-events-list'),
    path('birth/', BirthView.as_view(), name='repro-birth'),
    path('wean/', WeanView.as_view(), name='repro-wean'),
    path('<uuid:pk>/', ReproductiveEventViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='repro-events-detail'),
]
