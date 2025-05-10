# fraud_analysis_service/fraud_app/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

# Modelos para MongoDB (usando djongo)
class TransactionFeature(models.Model):
    """Características extraídas para análisis de fraude"""
    transaction_id = models.CharField(max_length=100, unique=True)
    sender_id = models.CharField(max_length=100)
    amount = models.FloatField()
    created_at = models.DateTimeField()
    hour_of_day = models.IntegerField()  # Hora del día (0-23)
    day_of_week = models.IntegerField()  # Día de la semana (0=lunes, 6=domingo)
    is_weekend = models.BooleanField()
    
    # Características derivadas
    sender_avg_amount = models.FloatField(default=0.0)  # Monto promedio de transacciones anteriores del remitente
    sender_transaction_count = models.IntegerField(default=0)  # Número de transacciones anteriores del remitente
    sender_transaction_frequency = models.FloatField(default=0.0)  # Frecuencia de transacciones (por día)
    amount_deviation = models.FloatField(default=0.0)  # Desviación del monto respecto al promedio del remitente
    
    # Resultado del análisis
    fraud_score = models.FloatField(default=0.0)  # Puntuación de fraude (0-1)
    is_fraud = models.BooleanField(default=False)  # Si se considera fraude (score > umbral)
    model_version = models.CharField(max_length=50, default='v1.0')  # Versión del modelo utilizado
    
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'característica de transacción'
        verbose_name_plural = 'características de transacciones'
    
    def __str__(self):
        return f"Análisis de transacción {self.transaction_id}: Score {self.fraud_score}"


class FraudModel(models.Model):
    """Modelo para el seguimiento de versiones del modelo de ML"""
    version = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    features_used = models.JSONField()  # Lista de características utilizadas
    model_file = models.CharField(max_length=255)  # Ruta al archivo del modelo
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    auc = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'modelo de fraude'
        verbose_name_plural = 'modelos de fraude'
    
    def __str__(self):
        return f"Modelo de Fraude v{self.version} - Accuracy: {self.accuracy:.2f}"


class UserActivityProfile(models.Model):
    """Perfil de actividad del usuario para detección de anomalías"""
    user_id = models.CharField(max_length=100, unique=True)
    avg_transaction_amount = models.FloatField(default=0.0)
    max_transaction_amount = models.FloatField(default=0.0)
    min_transaction_amount = models.FloatField(default=0.0)
    std_transaction_amount = models.FloatField(default=0.0)
    total_transactions = models.IntegerField(default=0)
    fraudulent_transactions = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    common_transaction_hours = models.JSONField(default=list)  # Lista de horas comunes
    common_transaction_days = models.JSONField(default=list)  # Lista de días comunes
    
    class Meta:
        verbose_name = 'perfil de usuario'
        verbose_name_plural = 'perfiles de usuario'
    
    def __str__(self):
        return f"Perfil de usuario {self.user_id} - {self.total_transactions} transacciones"
    
    def update_with_transaction(self, amount, created_at):
        """Actualizar perfil con una nueva transacción"""
        # Actualizar promedio (promedio ponderado)
        if self.total_transactions == 0:
            self.avg_transaction_amount = amount
            self.max_transaction_amount = amount
            self.min_transaction_amount = amount
            self.std_transaction_amount = 0.0
        else:
            # Actualizar máximo y mínimo
            self.max_transaction_amount = max(self.max_transaction_amount, amount)
            self.min_transaction_amount = min(self.min_transaction_amount, amount)
            
            # Recalcular promedio
            old_weight = self.total_transactions / (self.total_transactions + 1)
            new_weight = 1 / (self.total_transactions + 1)
            self.avg_transaction_amount = (old_weight * self.avg_transaction_amount) + (new_weight * amount)
            
            # Actualizar desviación estándar (aproximación)
            self.std_transaction_amount = (self.std_transaction_amount + 
                                         abs(amount - self.avg_transaction_amount)) / 2
        
        # Actualizar contadores
        self.total_transactions += 1
        
        # Actualizar hora y día común
        hour = created_at.hour
        day = created_at.weekday()
        
        # Convertir listas si es necesario
        if isinstance(self.common_transaction_hours, str):
            self.common_transaction_hours = eval(self.common_transaction_hours)
        if isinstance(self.common_transaction_days, str):
            self.common_transaction_days = eval(self.common_transaction_days)
            
        # Actualizar horas comunes
        if hour in self.common_transaction_hours:
            self.common_transaction_hours.remove(hour)
        self.common_transaction_hours.insert(0, hour)
        self.common_transaction_hours = self.common_transaction_hours[:5]  # Mantener solo las 5 más recientes
        
        # Actualizar días comunes
        if day in self.common_transaction_days:
            self.common_transaction_days.remove(day)
        self.common_transaction_days.insert(0, day)
        self.common_transaction_days = self.common_transaction_days[:5]  # Mantener solo los 5 más recientes
        
        self.save()

# Create your models here.
