from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransactionFeatureViewSet,
    FraudAnalysisView,
    FraudModelViewSet,
    UserActivityProfileViewSet
)

router = DefaultRouter()
router.register(r'features', TransactionFeatureViewSet, basename='transaction-feature')
router.register(r'models', FraudModelViewSet, basename='fraud-model')
router.register(r'profiles', UserActivityProfileViewSet, basename='user-profile')

urlpatterns = [
    path('', include(router.urls)),
    path('analyze/', FraudAnalysisView.as_view(), name='analyze-transaction'),
]