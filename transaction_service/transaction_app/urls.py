# transaction_service/transaction_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, TransactionStatViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'stats', TransactionStatViewSet, basename='transaction-stat')

urlpatterns = [
    path('', include(router.urls)),
]