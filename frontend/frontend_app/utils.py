import requests
import json
from datetime import datetime, timedelta

def debug_microservices_status():
    """Función para verificar el estado de todos los microservicios"""
    services = {
        'auth': 'http://localhost:8001/api/auth/',
        'transactions': 'http://localhost:8002/api/transactions/',
        'fraud': 'http://localhost:8003/api/fraud/'
    }
    
    status = {}
    
    for service_name, base_url in services.items():
        try:
            # Intentar una solicitud simple
            response = requests.get(f"{base_url}", timeout=5)
            status[service_name] = {
                'status': 'UP',
                'status_code': response.status_code,
                'url': base_url
            }
        except requests.exceptions.ConnectionError:
            status[service_name] = {
                'status': 'DOWN - Connection Error',
                'status_code': None,
                'url': base_url
            }
        except requests.exceptions.Timeout:
            status[service_name] = {
                'status': 'DOWN - Timeout',
                'status_code': None,
                'url': base_url
            }
        except Exception as e:
            status[service_name] = {
                'status': f'ERROR - {str(e)}',
                'status_code': None,
                'url': base_url
            }
    
    return status

def test_transaction_stats_endpoint(access_token):
    """Probar específicamente el endpoint de estadísticas de transacciones"""
    url = 'http://localhost:8002/api/transactions/transactions/stats/'
    headers = {'Authorization': f"Bearer {access_token}"}
    
    try:
        print(f"Testing stats endpoint: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': data,
                'formatted_data': format_stats_for_display(data)
            }
        else:
            return {
                'success': False,
                'status_code': response.status_code,
                'error': response.text
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def format_stats_for_display(stats_data):
    """Formatear los datos de estadísticas para mostrar de manera legible"""
    formatted = {}
    
    for period, data in stats_data.items():
        if isinstance(data, dict):
            formatted[period] = {
                'Total': data.get('total', 0),
                'Legítimas': data.get('legitimate', 0),
                'Posible Fraude': data.get('possibly_fraudulent', 0),
                'Fraudulentas': data.get('fraudulent', 0),
                'Monto Total': f"${data.get('total_amount', 0):,.2f}",
                'Distribución Diaria': len(data.get('daily_distribution', {}))
            }
    
    return formatted

def check_database_connections():
    """Verificar conexiones a las bases de datos"""
    # Para verificar que las bases de datos tengan datos
    connections_status = {}
    
    # Verificar transacciones
    try:
        from transaction_app.models import Transaction
        transaction_count = Transaction.objects.count()
        connections_status['transactions_db'] = {
            'status': 'Connected',
            'total_transactions': transaction_count
        }
    except Exception as e:
        connections_status['transactions_db'] = {
            'status': f'Error: {str(e)}',
            'total_transactions': 0
        }
    
    # Verificar análisis de fraude
    try:
        import sys
        sys.path.append('/path/to/fraud_analysis_service')  # Ajustar path según tu estructura
        # Esto podría no funcionar directamente, pero es un ejemplo
        connections_status['fraud_db'] = {
            'status': 'Cannot check directly',
            'note': 'Check via API endpoint'
        }
    except:
        connections_status['fraud_db'] = {
            'status': 'Cannot access',
            'note': 'Different Django instance'
        }
    
    return connections_status