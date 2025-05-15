#!/usr/bin/env python
"""
Script para realizar pruebas end-to-end del sistema de detección de fraude.

Este script:
1. Registra un usuario nuevo
2. Inicia sesión con ese usuario
3. Realiza una transacción
4. Verifica que la transacción ha sido creada
5. Verifica que el servicio de fraude ha analizado la transacción
"""
import requests
import json
import time
import random
import string
import sys
from datetime import datetime, date

# URLs de los microservicios
AUTH_SERVICE_URL = 'http://localhost:8001/api/auth/'
TRANSACTION_SERVICE_URL = 'http://localhost:8002/api/transactions/'
FRAUD_SERVICE_URL = 'http://localhost:8003/api/fraud/'

def generate_random_string(length=8):
    """Genera una cadena aleatoria de caracteres."""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

def generate_test_user():
    """Genera datos de usuario para pruebas."""
    random_suffix = generate_random_string(6).lower()
    return {
        "first_name": "Test",
        "last_name": "User",
        "id_number": f"1234567{random.randint(10000, 99999)}",
        "id_issue_date": "2020-01-01",
        "email": f"test.user.{random_suffix}@example.com",
        "phone_number": f"31012345{random.randint(10, 99)}",
        "password": "Test@123456",
        "password_confirm": "Test@123456"
    }

def register_user(user_data):
    """Registra un nuevo usuario."""
    print("\n=== Registrando nuevo usuario ===")
    print(f"Email: {user_data['email']}")
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}register/", 
            json=user_data,
            timeout=10
        )
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Usuario registrado exitosamente")
            return data.get('access'), data.get('user', {})
        else:
            print("❌ Error al registrar usuario")
            print(f"Respuesta: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, None

def login_user(email, password):
    """Inicia sesión con un usuario."""
    print("\n=== Iniciando sesión ===")
    print(f"Email: {email}")
    
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}login/", 
            json={"email": email, "password": password},
            timeout=10
        )
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login exitoso")
            return data.get('access'), data.get('user', {})
        else:
            print("❌ Error al iniciar sesión")
            print(f"Respuesta: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, None

def create_transaction(token, user_data, amount):
    """Crea una nueva transacción."""
    print("\n=== Creando transacción ===")
    
    transaction_data = {
        "sender_id": str(user_data.get('id')),
        "sender_name": f"{user_data.get('first_name')} {user_data.get('last_name')}",
        "receiver_name": f"Destinatario Prueba {generate_random_string(4)}",
        "amount": amount,
        "message": f"Transacción de prueba - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    print(f"Datos de transacción: {json.dumps(transaction_data, indent=2)}")
    
    try:
        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{TRANSACTION_SERVICE_URL}transactions/", 
            json=transaction_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Transacción creada exitosamente")
            print(f"ID de transacción: {data.get('id')}")
            print(f"Estado: {data.get('status')}")
            print(f"Score de fraude: {data.get('fraud_score')}")
            return data
        else:
            print("❌ Error al crear transacción")
            print(f"Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def get_user_transactions(token, user_id):
    """Obtiene las transacciones de un usuario."""
    print("\n=== Obteniendo transacciones del usuario ===")
    
    try:
        headers = {
            'Authorization': f"Bearer {token}"
        }
        
        response = requests.get(
            f"{TRANSACTION_SERVICE_URL}transactions/?sender_id={user_id}", 
            headers=headers,
            timeout=10
        )
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('results', [])
            print(f"✅ Se encontraron {len(transactions)} transacciones")
            return transactions
        else:
            print("❌ Error al obtener transacciones")
            print(f"Respuesta: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def check_fraud_service(transaction_id):
    """Verifica si el servicio de fraude ha analizado la transacción."""
    print("\n=== Verificando análisis de fraude ===")
    
    try:
        response = requests.get(
            f"{FRAUD_SERVICE_URL}features/?transaction_id={transaction_id}", 
            timeout=10
        )
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('results', [])
            
            if features:
                print("✅ Transacción analizada por el servicio de fraude")
                feature = features[0]
                print(f"Score de fraude: {feature.get('fraud_score')}")
                print(f"Es fraude: {feature.get('is_fraud')}")
                return feature
            else:
                print("❌ Transacción no encontrada en el servicio de fraude")
                return None
        else:
            print("❌ Error al consultar el servicio de fraude")
            print(f"Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def run_test():
    """Ejecuta la prueba end-to-end completa."""
    print("=== Iniciando prueba end-to-end ===")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Generar datos de usuario de prueba
    user_data = generate_test_user()
    
    # 2. Registrar usuario
    token, user = register_user(user_data)
    
    if not token or not user:
        print("No se pudo continuar la prueba debido a un error en el registro")
        return False
    
    # 3. Alternativamente, iniciar sesión si ya existe el usuario
    if not token or not user:
        token, user = login_user(user_data['email'], user_data['password'])
        
        if not token or not user:
            print("No se pudo continuar la prueba debido a un error en el login")
            return False
    
    # 4. Crear transacción
    amount = random.uniform(10, 500)  # Monto aleatorio entre 10 y 500
    transaction = create_transaction(token, user, amount)
    
    if not transaction:
        print("No se pudo continuar la prueba debido a un error al crear la transacción")
        return False
    
    # 5. Esperar unos segundos para que el servicio de fraude analice la transacción
    print("\nEsperando 3 segundos para que el servicio de fraude analice la transacción...")
    time.sleep(3)
    
    # 6. Obtener transacciones del usuario
    transactions = get_user_transactions(token, user.get('id'))
    
    if not transactions:
        print("No se encontraron transacciones para el usuario")
    else:
        print(f"Transacción más reciente: {transactions[0].get('id')}")
    
    # 7. Verificar análisis de fraude
    fraud_analysis = check_fraud_service(transaction.get('id'))
    
    # 8. Verificar resultado completo
    if transaction and fraud_analysis:
        print("\n=== Prueba end-to-end completada exitosamente ===")
        return True
    else:
        print("\n=== Prueba end-to-end completada con errores ===")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)