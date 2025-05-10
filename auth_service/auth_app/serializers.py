# auth_service/auth_app/serializers.py
from rest_framework import serializers
from .models import User, PasswordResetToken
import re
from django.utils import timezone
from datetime import timedelta
import uuid

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'id_number', 'id_issue_date', 
                  'email', 'phone_number', 'password', 'password_confirm', 'balance']
        extra_kwargs = {
            'id': {'read_only': True},
            'balance': {'read_only': True}
        }
    
    def validate_password(self, value):
        # Validar caracteres especiales, mayúsculas y números
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos una letra mayúscula.')
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos un carácter especial.')
        return value
    
    def validate(self, data):
        # Verificar que las contraseñas coinciden
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return data
    
    def create(self, validated_data):
        # Eliminar password_confirm ya que no es un campo del modelo
        validated_data.pop('password_confirm', None)
        
        # Crear usuario usando el manager personalizado
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            id_number=validated_data['id_number'],
            id_issue_date=validated_data['id_issue_date'],
            phone_number=validated_data['phone_number']
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'balance']
        read_only_fields = ['id', 'email', 'balance']

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Verificar que existe un usuario con este email
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No existe ningún usuario con este correo electrónico.')
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    password_confirm = serializers.CharField(style={'input_type': 'password'})
    
    def validate_token(self, value):
        try:
            token = PasswordResetToken.objects.get(token=value)
            if not token.is_valid():
                raise serializers.ValidationError('El token ha expirado o ya ha sido utilizado.')
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError('Token inválido.')
        return value
    
    def validate_password(self, value):
        # Validar caracteres especiales, mayúsculas y números
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos una letra mayúscula.')
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError('La contraseña debe contener al menos un carácter especial.')
        return value
    
    def validate(self, data):
        # Verificar que las contraseñas coinciden
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return data