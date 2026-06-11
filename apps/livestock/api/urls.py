from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnimalPhotoViewSet, AnimalViewSet

router = DefaultRouter()
router.register(prefix='animals', basename='animals', viewset=AnimalViewSet)

urlpatterns = [
    path('animals/<int:animal_id>/photos/', AnimalPhotoViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='animal-photos-list'),
    path('animals/<int:animal_id>/photos/<int:pk>/', AnimalPhotoViewSet.as_view({
        'get': 'retrieve',
        'delete': 'destroy',
    }), name='animal-photos-detail'),
    path('', include(router.urls)),
]
