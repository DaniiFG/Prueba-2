# auth_service/auth_app/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import re
from django.core.exceptions import ValidationError

def validate_password(password):
    """Valida que la contraseña cumpla con los requisitos: al menos un carácter especial, 
    una mayúscula y un número"""
    if not re.search(r'[A-Z]', password):
        raise ValidationError('La contraseña debe contener al menos una letra mayúscula.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('La contraseña debe contener al menos un número.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('La contraseña debe contener al menos un carácter especial.')

def validate_phone_number(value):
    """Valida que el número de teléfono sea numérico y tenga el formato correcto"""
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('El número telefónico debe tener 10 dígitos numéricos.')

def validate_id_number(value):
    """Valida que el número de cédula sea numérico y tenga el formato correcto"""
    if not re.match(r'^\d{8,12}$', value):
        raise ValidationError('El número de cédula debe tener entre 8 y 12 dígitos numéricos.')

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El Email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        
        # Validar la contraseña
        validate_password(password)
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField('nombres', max_length=100)
    last_name = models.CharField('apellidos', max_length=100)
    id_number = models.CharField('número de cédula', max_length=12, unique=True, validators=[validate_id_number])
    id_issue_date = models.DateField('fecha de expedición')
    email = models.EmailField('correo electrónico', unique=True)
    phone_number = models.CharField('número telefónico', max_length=10, validators=[validate_phone_number])
    balance = models.DecimalField('saldo disponible', max_digits=12, decimal_places=2, default=1000.00)
    
    # Campos requeridos por Django
    date_joined = models.DateTimeField('fecha de registro', auto_now_add=True)
    last_login = models.DateTimeField('último inicio de sesión', auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'id_number', 'id_issue_date', 'phone_number']
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'token de restablecimiento'
        verbose_name_plural = 'tokens de restablecimiento'
    
    def __str__(self):
        return f"Token para {self.user.email}"
    
    def is_valid(self):
        """Verifica si el token es válido"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

# Create your models here.
