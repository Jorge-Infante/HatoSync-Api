from rest_framework.routers import DefaultRouter

from .views import FarmViewSet

router_farms = DefaultRouter()
router_farms.register(prefix='', basename='farms', viewset=FarmViewSet)
