from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BreedViewSet, IdentificationTypeViewSet

router = DefaultRouter()
router.register('identification-types', IdentificationTypeViewSet, basename='identification-types')
router.register('breeds', BreedViewSet, basename='breeds')

urlpatterns = [
    path('', include(router.urls)),
]
