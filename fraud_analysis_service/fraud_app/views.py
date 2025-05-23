# fraud_analysis_service/fraud_app/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime
import pandas as pd
import numpy as np

from .models import TransactionFeature, FraudModel, UserActivityProfile
from .serializers import (
    TransactionFeatureSerializer,
    TransactionAnalysisRequestSerializer,
    TransactionAnalysisResponseSerializer,
    FraudModelSerializer,
    UserActivityProfileSerializer
)
from .ml_model.model import FraudDetectionModel
from .ml_model.train import train_model

class TransactionFeatureViewSet(viewsets.ReadOnlyModelViewSet):
    """Vista para consultar características extraídas de transacciones"""
    queryset = TransactionFeature.objects.all().order_by('-created_at')
    serializer_class = TransactionFeatureSerializer
    filterset_fields = ['transaction_id', 'sender_id', 'is_fraud']

class FraudAnalysisView(APIView):
    """Vista para analizar una transacción y determinar si es fraudulenta"""
    
    def post(self, request, format=None):
        """Recibir una transacción y analizarla"""
        print("Recibiendo solicitud de análisis de fraude:", request.data)
        
        # Validar datos de entrada
        serializer = TransactionAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            print("Errores de validación:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Obtener datos de la transacción
            transaction_data = serializer.validated_data
            transaction_id = transaction_data['transaction_id']
            sender_id = transaction_data['sender_id']
            amount = transaction_data['amount']
            created_at = transaction_data['created_at']
            
            print(f"Datos validados: ID={transaction_id}, sender={sender_id}, amount={amount}")
            
            # Convertir created_at a tipo datetime si es string
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Extraer características de la transacción
            features = self._extract_features(sender_id, amount, created_at)
            print(f"Características extraídas: {features}")
            
            # Crear entrada en TransactionFeature
            try:
                transaction_feature = TransactionFeature.objects.create(
                    transaction_id=transaction_id,
                    sender_id=sender_id,
                    amount=amount,
                    created_at=created_at,
                    hour_of_day=features['hour_of_day'],
                    day_of_week=features['day_of_week'],
                    is_weekend=features['is_weekend'],
                    sender_avg_amount=features['sender_avg_amount'],
                    sender_transaction_count=features['sender_transaction_count'],
                    sender_transaction_frequency=features['sender_transaction_frequency'],
                    amount_deviation=features['amount_deviation']
                )
                print(f"TransactionFeature creado: {transaction_feature.id}")
            except Exception as e:
                print(f"Error al crear TransactionFeature: {str(e)}")
                # Continuar incluso si hay error al guardar
                pass
            
            # Preparar datos para el modelo
            model_input = {
                'amount': amount,
                'created_at': created_at,
                'sender_avg_amount': features['sender_avg_amount'],
                'sender_transaction_count': features['sender_transaction_count'],
                'sender_transaction_frequency': features['sender_transaction_frequency'],
                'amount_deviation': features['amount_deviation']
            }
            
            # Cargar modelo y predecir
            try:
                model = FraudDetectionModel()
                prediction = model.predict(model_input)
                print(f"Predicción del modelo: {prediction}")
                
                # Actualizar TransactionFeature con los resultados
                if 'transaction_feature' in locals():
                    transaction_feature.fraud_score = prediction['fraud_score']
                    transaction_feature.is_fraud = prediction['is_fraud']
                    transaction_feature.model_version = prediction['model_version']
                    transaction_feature.save()
                
                # Actualizar perfil de usuario
                self._update_user_profile(sender_id, amount, created_at, prediction['is_fraud'])
                
            except Exception as e:
                print(f"Error en la predicción: {str(e)}")
                # Usar valores predeterminados si hay error
                prediction = {
                    'fraud_score': 0.1,
                    'is_fraud': False,
                    'confidence': 0.9,
                    'risk_factors': ["Error en análisis: se usa valor predeterminado"],
                    'model_version': 'error'
                }
            
            # Preparar respuesta
            response_data = {
                'transaction_id': transaction_id,
                'fraud_score': prediction['fraud_score'],
                'is_fraud': prediction['is_fraud'],
                'confidence': prediction['confidence'],
                'risk_factors': prediction['risk_factors'],
                'model_version': prediction['model_version']
            }
            
            print(f"Respuesta del análisis: {response_data}")
            
            # Serializar y retornar
            response_serializer = TransactionAnalysisResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data)
        
        except Exception as e:
            print(f"Error general en análisis de fraude: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _extract_features(self, sender_id, amount, created_at):
        """Extraer características para el análisis"""
        # Características temporales
        hour_of_day = created_at.hour
        day_of_week = created_at.weekday()
        is_weekend = day_of_week >= 5
        
        # Obtener o crear perfil del usuario
        user_profile, created = UserActivityProfile.objects.get_or_create(user_id=sender_id)
        
        # Características del remitente
        sender_avg_amount = user_profile.avg_transaction_amount
        sender_transaction_count = user_profile.total_transactions
        
        # Calcular frecuencia de transacciones (transacciones por día)
        if user_profile.last_active and user_profile.total_transactions > 0:
            days_active = max(1, (timezone.now() - user_profile.last_active).days)
            sender_transaction_frequency = user_profile.total_transactions / days_active
        else:
            sender_transaction_frequency = 0.0
        
        # Desviación del monto
        if sender_avg_amount > 0:
            amount_deviation = (amount - sender_avg_amount) / max(sender_avg_amount, 1)
        else:
            amount_deviation = 0.0
        
        return {
            'hour_of_day': hour_of_day,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'sender_avg_amount': sender_avg_amount,
            'sender_transaction_count': sender_transaction_count,
            'sender_transaction_frequency': sender_transaction_frequency,
            'amount_deviation': amount_deviation
        }
    
    def _update_user_profile(self, user_id, amount, created_at, is_fraud):
        """Actualizar perfil de actividad del usuario"""
        try:
            user_profile, created = UserActivityProfile.objects.get_or_create(user_id=user_id)
            user_profile.update_with_transaction(amount, created_at)
            
            if is_fraud:
                user_profile.fraudulent_transactions += 1
                user_profile.save()
                
        except Exception as e:
            print(f"Error al actualizar perfil de usuario: {str(e)}")

class FraudModelViewSet(viewsets.ReadOnlyModelViewSet):
    """Vista para consultar información de los modelos de ML"""
    queryset = FraudModel.objects.all().order_by('-created_at')
    serializer_class = FraudModelSerializer
    
    @action(detail=False, methods=['post'])
    def retrain(self, request):
        """Reentrenar el modelo con los datos históricos"""
        try:
            # Obtener datos históricos para reentrenamiento
            transaction_features = TransactionFeature.objects.all()
            
            if transaction_features.count() < 50:
                # Si hay pocos datos, entrenar con datos sintéticos
                result = train_model()
            else:
                # Crear DataFrame con datos históricos
                data = []
                for feature in transaction_features:
                    data.append({
                        'amount': feature.amount,
                        'hour_of_day': feature.hour_of_day,
                        'day_of_week': feature.day_of_week,
                        'is_weekend': feature.is_weekend,
                        'sender_avg_amount': feature.sender_avg_amount,
                        'sender_transaction_count': feature.sender_transaction_count,
                        'sender_transaction_frequency': feature.sender_transaction_frequency,
                        'amount_deviation': feature.amount_deviation,
                        'is_fraud': feature.is_fraud
                    })
                
                df = pd.DataFrame(data)
                result = train_model(df)
            
            return Response({
                'message': 'Modelo reentrenado exitosamente',
                'version': result['version'],
                'metrics': {
                    'accuracy': result['accuracy'],
                    'precision': result['precision'],
                    'recall': result['recall'],
                    'f1_score': result['f1_score'],
                    'auc': result['auc']
                }
            })
        
        except Exception as e:
            return Response({
                'error': 'Error al reentrenar el modelo',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserActivityProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """Vista para consultar perfiles de actividad de usuarios"""
    queryset = UserActivityProfile.objects.all()
    serializer_class = UserActivityProfileSerializer
    lookup_field = 'user_id'