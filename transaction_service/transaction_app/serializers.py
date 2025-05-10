# transaction_service/transaction_app/serializers.py
from rest_framework import serializers
from .models import Transaction, TransactionStat

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'sender_id', 'sender_name', 'receiver_name', 
            'amount', 'message', 'status', 'fraud_score', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'fraud_score', 'created_at', 'updated_at']
    
    def validate_amount(self, value):
        """Validar que el monto sea positivo y mayor que cero"""
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que cero.")
        return value

class TransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['sender_id', 'sender_name', 'receiver_name', 'amount', 'message']
    
    def validate_amount(self, value):
        """Validar que el monto sea positivo y mayor que cero"""
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que cero.")
        return value

class TransactionUpdateStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['status']
        
    def validate_status(self, value):
        """Validar que el estado sea uno de los permitidos"""
        valid_statuses = [status[0] for status in Transaction.TRANSACTION_STATUS]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Estado inválido. Opciones válidas: {', '.join(valid_statuses)}")
        return value

class TransactionStatSerializer(serializers.ModelSerializer):
    legitimate_percentage = serializers.FloatField(read_only=True)
    possibly_fraudulent_percentage = serializers.FloatField(read_only=True)
    fraudulent_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = TransactionStat
        fields = [
            'date', 'total_transactions', 'legitimate_count',
            'possibly_fraudulent_count', 'fraudulent_count', 'total_amount',
            'legitimate_percentage', 'possibly_fraudulent_percentage', 'fraudulent_percentage'
        ]
        read_only_fields = fields