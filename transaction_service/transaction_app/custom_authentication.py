# transaction_service/transaction_app/custom_authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            # Solo verificamos que el token sea válido, no buscamos al usuario
            validated_token = UntypedToken(raw_token)
            
            # Creamos un usuario "falso" con los datos del token
            user_id = validated_token.get('user_id')
            
            if not user_id:
                raise AuthenticationFailed('Token no contiene user_id', code='invalid_token')
            
            # Crear un objeto ficticio de usuario
            user = type('SimpleUser', (), {
                'id': user_id,
                'is_authenticated': True,
                'is_active': True,
                '__str__': lambda self: f"User {self.id}"
            })
            
            return (user, validated_token)
        except TokenError as e:
            raise InvalidToken(e.args[0])