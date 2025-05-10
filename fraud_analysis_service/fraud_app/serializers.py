# fraud_analysis_service/fraud_app/serializers.py
from rest_framework import serializers
from .models import TransactionFeature, FraudModel, UserActivityProfile

class TransactionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionFeature
        fields = '__all__'
        read_only_fields = [
            'hour_of_day', 'day_of_week', 'is_weekend', 
            'sender_avg_amount', 'sender_transaction_count', 
            'sender_transaction_frequency', 'amount_deviation',
            'fraud_score', 'is_fraud', 'model_version', 'processed_at'
        ]

class TransactionAnalysisRequestSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=100)
    sender_id = serializers.CharField(max_length=100)
    amount = serializers.FloatField(min_value=0.01)
    created_at = serializers.DateTimeField()

class TransactionAnalysisResponseSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=100)
    fraud_score = serializers.FloatField()
    is_fraud = serializers.BooleanField()
    confidence = serializers.FloatField()
    risk_factors = serializers.ListField(child=serializers.CharField(), required=False)
    model_version = serializers.CharField()

class FraudModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudModel
        fields = '__all__'
        read_only_fields = ['created_at']

class UserActivityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityProfile
        fields = '__all__'
        read_only_fields = ['last_active']