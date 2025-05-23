from django.urls import path
from . import views

urlpatterns = [
    # Páginas públicas
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.password_reset_request, name='password_reset'),
    path('reset-password/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Panel de usuario
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('transaction/new/', views.transaction_form, name='transaction_form'),
    
    # Panel de administrador
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/transactions/', views.admin_transactions, name='admin_transactions'),
    
    # API para AJAX
    path('api/update-transaction-status/', views.update_transaction_status, name='update_transaction_status'),
    path('api/dashboard/stats/', views.get_dashboard_stats, name='dashboard_stats'),
    path('api/transactions/recent/', views.get_recent_transactions, name='recent_transactions'),
]