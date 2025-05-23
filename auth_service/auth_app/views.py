# auth_service/auth_app/views.py
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import User, PasswordResetToken
from .serializers import (
    UserSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generar tokens JWT para el nuevo usuario
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=email, password=password)
        
        if user is None:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserProfileSerializer(user).data
        })

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Crear token para restablecimiento
        token_value = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(hours=1)
        
        # Guardar token en la base de datos
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token_value,
            expires_at=expires_at
        )
        
        # Crear enlace de restablecimiento (aquí usarías la URL de tu frontend)
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{token_value}"
        
        # Enviar correo con el enlace de restablecimiento
        send_mail(
            'Restablecimiento de contraseña',
            f'Hola {user.first_name},\n\nHaz clic en el siguiente enlace para restablecer tu contraseña:\n{reset_link}\n\nEste enlace expirará en 1 hora.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return Response({'message': 'Se ha enviado un correo con instrucciones para restablecer tu contraseña.'}, 
                        status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token_value = serializer.validated_data['token']
        password = serializer.validated_data['password']
        
        # Obtener token y usuario
        reset_token = PasswordResetToken.objects.get(token=token_value)
        user = reset_token.user
        
        # Cambiar contraseña
        user.set_password(password)
        user.save()
        
        # Marcar token como usado
        reset_token.is_used = True
        reset_token.save()
        
        # Generar nuevos tokens JWT para el usuario
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Contraseña restablecida con éxito.',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_info(request, user_id):
    """Endpoint para obtener información básica de un usuario por ID"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        user_data = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'balance': float(user.balance)
        }
        
        return JsonResponse(user_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)