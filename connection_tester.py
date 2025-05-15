#!/usr/bin/env python
"""
Script para verificar la conexión entre los microservicios.
"""
import requests
import json
import sys
import time

# URLs de los microservicios
AUTH_SERVICE_URL = 'http://localhost:8001/api/auth/'
TRANSACTION_SERVICE_URL = 'http://localhost:8002/api/transactions/'
FRAUD_SERVICE_URL = 'http://localhost:8003/api/fraud/'

def test_auth_service():
    """Probar la conexión con el servicio de autenticación."""
    print("\n=== Probando servicio de autenticación ===")
    try:
        # Prueba básica de conexión
        response = requests.get(AUTH_SERVICE_URL.rstrip('/') + '/admin/')
        
        if response.status_code in [200, 301, 302, 401, 403]:
            print(f"✅ Conexión exitosa (código: {response.status_code})")
        else:
            print(f"❌ Error de conexión (código: {response.status_code})")
            
        # Probar login con credenciales de prueba
        try:
            login_data = {
                "email": "test@example.com",
                "password": "Test@123"
            }
            response = requests.post(AUTH_SERVICE_URL + 'login/', json=login_data)
            
            if response.status_code == 200:
                print("✅ Login exitoso")
                json_resp = response.json()
                
                if 'access' in json_resp and 'refresh' in json_resp and 'user' in json_resp:
                    print("✅ Respuesta completa con tokens y datos de usuario")
                    # Guardar token para pruebas posteriores
                    return json_resp.get('access'), json_resp.get('user', {}).get('id')
                else:
                    print("❌ Respuesta incompleta")
                    print(f"Respuesta: {json_resp}")
            elif response.status_code == 401:
                print("❌ Credenciales inválidas (error esperado si no existe el usuario)")
            else:
                print(f"❌ Error en login (código: {response.status_code})")
                print(f"Respuesta: {response.text}")
        except Exception as e:
            print(f"❌ Error al intentar login: {str(e)}")
            
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {str(e)}")
    
    return None, None

def test_transaction_service(auth_token=None, user_id=None):
    """Probar la conexión con el servicio de transacciones."""
    print("\n=== Probando servicio de transacciones ===")
    try:
        # Prueba básica de conexión
        response = requests.get(TRANSACTION_SERVICE_URL)
        
        if response.status_code in [200, 401, 403]:
            print(f"✅ Conexión exitosa (código: {response.status_code})")
        else:
            print(f"❌ Error de conexión (código: {response.status_code})")
        
        # Si tenemos token de autorización, probamos obtener transacciones
        if auth_token and user_id:
            headers = {'Authorization': f'Bearer {auth_token}'}
            
            # Probar obtener transacciones del usuario
            try:
                response = requests.get(
                    f"{TRANSACTION_SERVICE_URL}transactions/?sender_id={user_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    json_resp = response.json()
                    print("✅ Obtención de transacciones exitosa")
                    print(f"Transacciones: {len(json_resp.get('results', []))}")
                elif response.status_code == 401:
                    print("❌ Token no válido")
                else:
                    print(f"❌ Error al obtener transacciones (código: {response.status_code})")
                    print(f"Respuesta: {response.text}")
            except Exception as e:
                print(f"❌ Error al obtener transacciones: {str(e)}")
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {str(e)}")

def test_fraud_service():
    """Probar la conexión con el servicio de análisis de fraude."""
    print("\n=== Probando servicio de análisis de fraude ===")
    try:
        # Prueba básica de conexión
        response = requests.get(FRAUD_SERVICE_URL)
        
        if response.status_code in [200, 401, 403]:
            print(f"✅ Conexión exitosa (código: {response.status_code})")
        else:
            print(f"❌ Error de conexión (código: {response.status_code})")
        
        # Probar análisis de fraude con datos de prueba
        try:
            sample_data = {
                'transaction_id': 'test-transaction-id',
                'sender_id': 'test-user-id',
                'amount': 100.0,
                'created_at': '2023-01-01T12:00:00Z'
            }
            
            response = requests.post(FRAUD_SERVICE_URL + 'analyze/', json=sample_data)
            
            if response.status_code == 200:
                json_resp = response.json()
                print("✅ Análisis de fraude exitoso")
                print(f"Score de fraude: {json_resp.get('fraud_score')}")
                print(f"Es fraude: {json_resp.get('is_fraud')}")
            else:
                print(f"❌ Error en análisis de fraude (código: {response.status_code})")
                print(f"Respuesta: {response.text}")
        except Exception as e:
            print(f"❌ Error al analizar fraude: {str(e)}")
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {str(e)}")

def run_all_tests():
    """Ejecutar todas las pruebas de conexión."""
    print("=== Iniciando pruebas de conexión entre microservicios ===")
    print(f"Fecha y hora: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Probar servicios individuales
    token, user_id = test_auth_service()
    test_transaction_service(token, user_id)
    test_fraud_service()
    
    print("\n=== Pruebas completadas ===")

if __name__ == "__main__":
    run_all_tests()