# transaction_service/transaction_app/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Sum, Q
import requests
from datetime import datetime, timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from .models import Transaction, TransactionStat
from .serializers import (
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionUpdateStatusSerializer,
    TransactionStatSerializer
)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'sender_id']
    ordering_fields = ['created_at', 'amount', 'fraud_score']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Permitir acceso no autenticado para listar, crear y recuperar transacciones.
        """
        if self.action in ['list', 'create', 'retrieve', 'update_status']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Personalizar el queryset según la acción y el usuario.
        """
        queryset = super().get_queryset()
        return queryset
    
    # Añadir estas líneas:
    def get_permissions(self):
        """
        Permitir acceso no autenticado para listar y crear transacciones,
        pero requerir autenticación para otras acciones.
        """
        if self.action in ['list', 'create', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TransactionCreateSerializer
        elif self.action == 'update_status':
            return TransactionUpdateStatusSerializer
        return TransactionSerializer
    
    def create(self, request, *args, **kwargs):
        print("Datos recibidos para crear transacción:", request.data)
        
        # Debug adicional
        print("Cabeceras:", request.headers)
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            transaction = serializer.save()
            print(f"Transacción creada exitosamente: {transaction.id}")
            
            # Simplificamos esta parte temporalmente
            # Marcamos la transacción como legítima por defecto
            transaction.status = 'legitimate'
            transaction.fraud_score = 0.1
            transaction.save()
            
            # Actualizar estadísticas diarias
            try:
                self._update_transaction_stats(transaction)
            except Exception as e:
                print(f"Error al actualizar estadísticas: {str(e)}")
            
            # Retornar la transacción creada
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print(f"Error general al procesar la transacción: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        transaction = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtener estado anterior para ajustar estadísticas
        old_status = transaction.status
        
        # Actualizar estado
        transaction.status = serializer.validated_data['status']
        transaction.save()
        
        # Actualizar estadísticas
        self._adjust_transaction_stats(transaction, old_status)
        
        return Response(TransactionSerializer(transaction).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de transacciones para períodos específicos"""
        today = timezone.now().date()
        
        # Estadísticas del día actual
        today_stats = self._get_period_stats(today, today)
        
        # Estadísticas de la última semana
        week_start = today - timedelta(days=6)
        week_stats = self._get_period_stats(week_start, today)
        
        # Estadísticas del último mes
        month_start = today - timedelta(days=29)
        month_stats = self._get_period_stats(month_start, today)
        
        return Response({
            'today': today_stats,
            'last_week': week_stats,
            'last_month': month_stats
        })
    
    @action(detail=False, methods=['get'])
    def filter_by_amount(self, request):
        """Filtrar transacciones por rango de monto"""
        min_amount = request.query_params.get('min', None)
        max_amount = request.query_params.get('max', None)
        
        queryset = self.get_queryset()
        
        if min_amount:
            queryset = queryset.filter(amount__gte=float(min_amount))
        if max_amount:
            queryset = queryset.filter(amount__lte=float(max_amount))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _get_period_stats(self, start_date, end_date):
        """Obtener estadísticas para un período dado"""
        transactions = Transaction.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        
        stats = {
            'total': transactions.count(),
            'legitimate': transactions.filter(status='legitimate').count(),
            'possibly_fraudulent': transactions.filter(status='possibly_fraudulent').count(),
            'fraudulent': transactions.filter(status='fraudulent').count(),
            'total_amount': sum([t.amount for t in transactions]),
        }
        
        # Calcular distribución por día para gráficos
        daily_counts = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_counts[date_str] = transactions.filter(created_at__date=current_date).count()
            current_date += timedelta(days=1)
        
        stats['daily_distribution'] = daily_counts
        
        return stats
    
    def _update_transaction_stats(self, transaction):
        """Actualizar estadísticas diarias con una nueva transacción"""
        transaction_date = transaction.created_at.date()
        
        # Obtener o crear estadísticas para la fecha
        stat, created = TransactionStat.objects.get_or_create(date=transaction_date)
        
        # Actualizar contadores
        stat.total_transactions += 1
        stat.total_amount += transaction.amount
        
        if transaction.status == 'legitimate':
            stat.legitimate_count += 1
        elif transaction.status == 'possibly_fraudulent':
            stat.possibly_fraudulent_count += 1
        elif transaction.status == 'fraudulent':
            stat.fraudulent_count += 1
        
        stat.save()
    
    def _adjust_transaction_stats(self, transaction, old_status):
        """Ajustar estadísticas cuando cambia el estado de una transacción"""
        transaction_date = transaction.created_at.date()
        new_status = transaction.status
        
        if old_status == new_status:
            return  # No hay cambio en el estado
        
        stat, created = TransactionStat.objects.get_or_create(date=transaction_date)
        
        # Restar del estado anterior
        if old_status == 'legitimate':
            stat.legitimate_count = max(0, stat.legitimate_count - 1)
        elif old_status == 'possibly_fraudulent':
            stat.possibly_fraudulent_count = max(0, stat.possibly_fraudulent_count - 1)
        elif old_status == 'fraudulent':
            stat.fraudulent_count = max(0, stat.fraudulent_count - 1)
        
        # Sumar al nuevo estado
        if new_status == 'legitimate':
            stat.legitimate_count += 1
        elif new_status == 'possibly_fraudulent':
            stat.possibly_fraudulent_count += 1
        elif new_status == 'fraudulent':
            stat.fraudulent_count += 1
        
        stat.save()
    
    def _send_fraud_notification(self, transaction):
        """Simular envío de notificación cuando se detecta fraude"""
        print(f"¡ALERTA DE FRAUDE! Transacción {transaction.id} detectada como fraudulenta.")
        # Aquí implementarías la lógica real de notificación (WebSockets, emails, etc.)

class TransactionStatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionStat.objects.all()
    serializer_class = TransactionStatSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']
    ordering = ['-date']

# Create your views here.
