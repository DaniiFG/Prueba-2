# transaction_service/transaction_app/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.mail import send_mail
from django.conf import settings
import requests
from datetime import datetime, timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
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
        """Permitir acceso no autenticado para listar, crear y recuperar transacciones."""
        if self.action in ['list', 'create', 'retrieve', 'update_status']:
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
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            transaction = serializer.save()
            print(f"Transacción creada exitosamente: {transaction.id}")
            
            # Analizar la transacción con el servicio de fraude
            fraud_result = self._analyze_transaction_for_fraud(transaction)
            
            # Actualizar la transacción con el resultado del análisis
            if fraud_result:
                transaction.fraud_score = fraud_result.get('fraud_score', 0.0)
                
                # Determinar el estado basado en el score
                if fraud_result.get('is_fraud', False):
                    transaction.status = 'fraudulent'
                elif fraud_result.get('fraud_score', 0) > 0.5:
                    transaction.status = 'possibly_fraudulent'
                else:
                    transaction.status = 'legitimate'
                
                transaction.save()
                
                # Enviar notificación por correo al usuario
                self._send_transaction_notification(transaction, fraud_result)
            else:
                # Si no se pudo analizar, marcar como legítima por defecto
                transaction.status = 'legitimate'
                transaction.fraud_score = 0.1
                transaction.save()
                
                # Enviar notificación básica
                self._send_transaction_notification(transaction, None)
            
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
    
    def _analyze_transaction_for_fraud(self, transaction):
        """Enviar transacción al servicio de análisis de fraude"""
        try:
            fraud_service_url = getattr(settings, 'FRAUD_ANALYSIS_SERVICE_URL', 'http://localhost:8003/api/fraud/')
            
            # Preparar datos para el análisis
            analysis_data = {
                'transaction_id': str(transaction.id),
                'sender_id': transaction.sender_id,
                'amount': float(transaction.amount),
                'created_at': transaction.created_at.isoformat()
            }
            
            print(f"Enviando transacción para análisis: {analysis_data}")
            
            # Realizar solicitud al servicio de fraude
            response = requests.post(
                f"{fraud_service_url}analyze/",
                json=analysis_data,
                timeout=30
            )
            
            print(f"Respuesta del servicio de fraude: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Resultado del análisis: {result}")
                return result
            else:
                print(f"Error en el servicio de fraude: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error al comunicarse con el servicio de fraude: {str(e)}")
            return None
    
    def _send_transaction_notification(self, transaction, fraud_result):
        """Enviar notificación por correo electrónico al usuario"""
        try:
            # Obtener información del usuario desde el servicio de autenticación
            user_info = self._get_user_info(transaction.sender_id)
            
            if not user_info or not user_info.get('email'):
                print("No se pudo obtener el email del usuario")
                return
            
            user_email = user_info['email']
            user_name = user_info.get('first_name', 'Usuario')
            
            # Preparar el contenido del correo según el estado
            if transaction.status == 'legitimate':
                subject = "✅ Transacción Exitosa - Legítima"
                status_message = "Tu transacción ha sido procesada exitosamente y clasificada como legítima."
                status_color = "green"
            elif transaction.status == 'possibly_fraudulent':
                subject = "⚠️ Transacción en Revisión - Posible Fraude"
                status_message = "Tu transacción está siendo revisada por nuestro equipo de seguridad debido a patrones inusuales."
                status_color = "orange"
            else:  # fraudulent
                subject = "🚨 Transacción Bloqueada - Fraude Detectado"
                status_message = "Tu transacción ha sido bloqueada por medidas de seguridad. Si crees que esto es un error, contacta soporte."
                status_color = "red"
            
            # Crear mensaje de correo
            message = f"""
Hola {user_name},

{status_message}

DETALLES DE LA TRANSACCIÓN:
• ID: {str(transaction.id)[:8]}...
• Destinatario: {transaction.receiver_name}
• Monto: ${transaction.amount}
• Fecha: {transaction.created_at.strftime('%d/%m/%Y %H:%M')}
• Estado: {transaction.get_status_display_name()}
• Puntuación de Riesgo: {transaction.fraud_score:.1%}

"""
            
            # Agregar factores de riesgo si están disponibles
            if fraud_result and fraud_result.get('risk_factors'):
                message += "FACTORES DE RIESGO DETECTADOS:\n"
                for factor in fraud_result['risk_factors']:
                    message += f"• {factor}\n"
                message += "\n"
            
            message += """
Si tienes alguna pregunta o inquietud, no dudes en contactarnos.

Atentamente,
Equipo de Seguridad
Sistema Anti-Fraude
"""
            
            # Enviar correo electrónico
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@antifraude.com'),
                recipient_list=[user_email],
                fail_silently=False,
            )
            
            print(f"Notificación enviada a {user_email} para transacción {transaction.id}")
            
        except Exception as e:
            print(f"Error al enviar notificación por correo: {str(e)}")
    
    def _get_user_info(self, user_id):
        """Obtener información del usuario desde el servicio de autenticación"""
        try:
            auth_service_url = getattr(settings, 'AUTH_SERVICE_URL', 'http://localhost:8001/api/auth/')
            
            # Realizar solicitud al servicio de autenticación
            response = requests.get(
                f"{auth_service_url}user/{user_id}/",
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"Información del usuario obtenida: {user_data.get('email')}")
                return user_data
            else:
                print(f"Error al obtener información del usuario: {response.status_code}")
                return None
            
        except Exception as e:
            print(f"Error al comunicarse con el servicio de autenticación: {str(e)}")
            return None
    
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
    
    # transaction_service/transaction_app/views.py - Método stats actualizado

# transaction_service/transaction_app/views.py - Método stats corregido

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de transacciones para períodos específicos"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        from django.db.models import Count, Sum, Q
        
        try:
            # Usar timezone.now() para obtener la fecha/hora actual con zona horaria
            now = timezone.now()
            today = now.date()
            
            print(f"Calculando estadísticas para la fecha: {today}")
            
            # Estadísticas del día actual
            today_stats = self._get_period_stats_improved(today, today)
            print(f"Estadísticas de hoy: {today_stats}")
            
            # Estadísticas de la última semana
            week_start = today - timedelta(days=6)
            week_stats = self._get_period_stats_improved(week_start, today)
            print(f"Estadísticas de la semana: {week_stats}")
            
            # Estadísticas del último mes
            month_start = today - timedelta(days=29)
            month_stats = self._get_period_stats_improved(month_start, today)
            print(f"Estadísticas del mes: {month_stats}")
            
            response_data = {
                'today': today_stats,
                'last_week': week_stats,
                'last_month': month_stats,
                'generated_at': now.isoformat()
            }
            
            print(f"Respuesta completa de estadísticas: {response_data}")
            
            return Response(response_data)
            
        except Exception as e:
            print(f"Error en el endpoint de estadísticas: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Retornar estructura vacía en caso de error
            return Response({
                'today': {'total': 0, 'legitimate': 0, 'possibly_fraudulent': 0, 'fraudulent': 0, 'total_amount': 0.0},
                'last_week': {'total': 0, 'legitimate': 0, 'possibly_fraudulent': 0, 'fraudulent': 0, 'total_amount': 0.0, 'daily_distribution': {}},
                'last_month': {'total': 0, 'legitimate': 0, 'possibly_fraudulent': 0, 'fraudulent': 0, 'total_amount': 0.0, 'daily_distribution': {}},
                'error': str(e)
            })
    
    def _get_period_stats_improved(self, start_date, end_date):
        """Obtener estadísticas para un período dado - VERSIÓN MEJORADA"""
        from collections import defaultdict
        from django.db.models import Count, Sum, Q
        from django.utils import timezone
        
        try:
            print(f"Obteniendo estadísticas desde {start_date} hasta {end_date}")
            
            # Convertir las fechas a datetime con timezone para el filtro
            start_datetime = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time()),
                timezone.get_current_timezone()
            )
            end_datetime = timezone.make_aware(
                datetime.combine(end_date, datetime.max.time()),
                timezone.get_current_timezone()
            )
            
            # Obtener todas las transacciones del período
            transactions = Transaction.objects.filter(
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
            
            print(f"Transacciones encontradas: {transactions.count()}")
            
            # Usar agregación para obtener estadísticas
            stats_aggregate = transactions.aggregate(
                total=Count('id'),
                total_amount=Sum('amount'),
                legitimate=Count('id', filter=Q(status='legitimate')),
                possibly_fraudulent=Count('id', filter=Q(status='possibly_fraudulent')),
                fraudulent=Count('id', filter=Q(status='fraudulent'))
            )
            
            # Preparar estadísticas
            stats = {
                'total': stats_aggregate['total'] or 0,
                'legitimate': stats_aggregate['legitimate'] or 0,
                'possibly_fraudulent': stats_aggregate['possibly_fraudulent'] or 0,
                'fraudulent': stats_aggregate['fraudulent'] or 0,
                'total_amount': float(stats_aggregate['total_amount'] or 0),
            }
            
            # Obtener distribución diaria
            daily_distribution = {}
            current_date = start_date
            
            while current_date <= end_date:
                # Contar transacciones para cada día
                day_start = timezone.make_aware(
                    datetime.combine(current_date, datetime.min.time()),
                    timezone.get_current_timezone()
                )
                day_end = timezone.make_aware(
                    datetime.combine(current_date, datetime.max.time()),
                    timezone.get_current_timezone()
                )
                
                day_count = transactions.filter(
                    created_at__gte=day_start,
                    created_at__lte=day_end
                ).count()
                
                date_key = current_date.strftime('%Y-%m-%d')
                daily_distribution[date_key] = day_count
                
                current_date += timedelta(days=1)
            
            stats['daily_distribution'] = daily_distribution
            
            print(f"Estadísticas calculadas: {stats}")
            
            return stats
            
        except Exception as e:
            print(f"Error al calcular estadísticas del período: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'total': 0,
                'legitimate': 0,
                'possibly_fraudulent': 0,
                'fraudulent': 0,
                'total_amount': 0.0,
                'daily_distribution': {}
            }
    
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
            'total_amount': float(sum([t.amount for t in transactions])),
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

class TransactionStatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionStat.objects.all()
    serializer_class = TransactionStatSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']
    ordering = ['-date']