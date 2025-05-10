# transaction_service/transaction_app/models.py
from django.db import models
import uuid

class Transaction(models.Model):
    TRANSACTION_STATUS = (
        ('legitimate', 'Legítima'),
        ('possibly_fraudulent', 'Posiblemente Fraudulenta'),
        ('fraudulent', 'Fraudulenta'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_id = models.CharField(max_length=100)  # ID del usuario que envía el dinero
    sender_name = models.CharField(max_length=200)  # Nombre completo del remitente
    receiver_name = models.CharField(max_length=200)  # Nombre del destinatario
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    message = models.TextField(blank=True, null=True)  # Mensaje opcional
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='legitimate')
    fraud_score = models.FloatField(default=0.0)  # Score de 0 a 1, donde 1 es alta probabilidad de fraude
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'transacción'
        verbose_name_plural = 'transacciones'
    
    def __str__(self):
        return f"{self.sender_name} -> {self.receiver_name}: ${self.amount}"
    
    def get_status_display_name(self):
        return dict(self.TRANSACTION_STATUS).get(self.status, 'Desconocido')
    
    @property
    def formatted_amount(self):
        return "${:,.2f}".format(self.amount)
    
    @property
    def short_id(self):
        """Retorna una versión corta del UUID para visualización"""
        return str(self.id)[:8]
    
    def mark_as_fraudulent(self):
        """Marcar transacción como fraudulenta"""
        self.status = 'fraudulent'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_legitimate(self):
        """Marcar transacción como legítima"""
        self.status = 'legitimate'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_possibly_fraudulent(self):
        """Marcar transacción como posiblemente fraudulenta"""
        self.status = 'possibly_fraudulent'
        self.save(update_fields=['status', 'updated_at'])

class TransactionStat(models.Model):
    """Modelo para estadísticas de transacciones"""
    date = models.DateField(unique=True)
    total_transactions = models.IntegerField(default=0)
    legitimate_count = models.IntegerField(default=0)
    possibly_fraudulent_count = models.IntegerField(default=0)
    fraudulent_count = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'estadística de transacción'
        verbose_name_plural = 'estadísticas de transacciones'
    
    def __str__(self):
        return f"Estadísticas del {self.date}: {self.total_transactions} transacciones"
    
    @property
    def legitimate_percentage(self):
        """Porcentaje de transacciones legítimas"""
        if self.total_transactions == 0:
            return 0
        return (self.legitimate_count / self.total_transactions) * 100
    
    @property
    def possibly_fraudulent_percentage(self):
        """Porcentaje de transacciones posiblemente fraudulentas"""
        if self.total_transactions == 0:
            return 0
        return (self.possibly_fraudulent_count / self.total_transactions) * 100
    
    @property
    def fraudulent_percentage(self):
        """Porcentaje de transacciones fraudulentas"""
        if self.total_transactions == 0:
            return 0
        return (self.fraudulent_count / self.total_transactions) * 100

# Create your models here.
