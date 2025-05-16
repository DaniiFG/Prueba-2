# frontend/frontend_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from datetime import datetime, timedelta

# URLs de los microservicios
AUTH_SERVICE_URL = 'http://localhost:8001/api/auth/'
TRANSACTION_SERVICE_URL = 'http://localhost:8002/api/transactions/'
FRAUD_SERVICE_URL = 'http://localhost:8003/api/fraud/'

def index(request):
    """Vista de la página principal"""
    return render(request, 'index.html')

def login_view(request):
    print("\n==== DEBUG LOGIN VIEW ====")
    print(f"Método: {request.method}")
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(f"Email: {email}")
        print(f"Autenticando con: http://localhost:8001/api/auth/login/")
        
        try:
            response = requests.post(
                "http://localhost:8001/api/auth/login/",
                json={"email": email, "password": password}
            )
            print(f"Código de respuesta: {response.status_code}")
            print(f"Contenido: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Datos recibidos: {data.keys()}")
            
                # Guarda en sesión e imprime
                request.session['access_token'] = data.get('access', '')
                request.session['refresh_token'] = data.get('refresh', '')  # Guardar también el token de refresco
                request.session['user_data'] = data.get('user', {})
                print(f"Guardado en sesión: {request.session.get('access_token')[:10]}... y {request.session.get('user_data')}")
                request.session.modified = True
                                
                # Redirigir
                print("Redirigiendo a dashboard")
                return redirect('user_dashboard')
            else:
                print(f"Error en autenticación: {response.text}")
        except Exception as e:
            print(f"Excepción: {str(e)}")
    
    print("Retornando formulario de login")
    return render(request, 'registration/login.html')

def register_view(request):
    """Vista de registro de usuario"""
    if request.method == 'POST':
        # Recopilar datos del formulario
        user_data = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'id_number': request.POST.get('id_number'),
            'id_issue_date': request.POST.get('id_issue_date'),
            'email': request.POST.get('email'),
            'phone_number': request.POST.get('phone_number'),
            'password': request.POST.get('password'),
            'password_confirm': request.POST.get('password_confirm'),
        }
        
        # Validar contraseñas
        if user_data['password'] != user_data['password_confirm']:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'registration/register.html')
        
        # Llamar al servicio de autenticación
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}register/", 
                json=user_data
            )
            
            if response.status_code == 201:
                # Registro exitoso
                messages.success(request, 'Registro exitoso, ahora puedes iniciar sesión')
                return redirect('login')
            else:
                # Error de registro
                error_data = response.json()
                for field, errors in error_data.items():
                    if isinstance(errors, list):
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
                    else:
                        messages.error(request, f'{field}: {errors}')
        except Exception as e:
            messages.error(request, f'Error de conexión: {str(e)}')
    
    return render(request, 'registration/register.html')

def logout_view(request):
    """Vista para cerrar sesión"""
    # Limpiar sesión
    if 'access_token' in request.session:
        del request.session['access_token']
    if 'refresh_token' in request.session:
        del request.session['refresh_token']
    if 'user_data' in request.session:
        del request.session['user_data']
    
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')

def password_reset_request(request):
    """Vista para solicitar restablecimiento de contraseña"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Llamar al servicio de autenticación
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}password/reset/", 
                json={"email": email}
            )
            
            if response.status_code == 200:
                messages.success(request, 'Se ha enviado un correo con instrucciones para restablecer tu contraseña')
                return redirect('login')
            else:
                messages.error(request, 'No se encontró ningún usuario con ese correo electrónico')
        except Exception as e:
            messages.error(request, f'Error de conexión: {str(e)}')
    
    return render(request, 'registration/password_reset.html')

def password_reset_confirm(request, token):
    """Vista para confirmar restablecimiento de contraseña"""
    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validar contraseñas
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'registration/password_reset_confirm.html', {'token': token})
        
        # Llamar al servicio de autenticación
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}password/reset/confirm/", 
                json={
                    "token": token,
                    "password": password,
                    "password_confirm": password_confirm
                }
            )
            
            if response.status_code == 200:
                messages.success(request, 'Contraseña restablecida correctamente')
                return redirect('login')
            else:
                error_data = response.json()
                for field, errors in error_data.items():
                    if isinstance(errors, list):
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
                    else:
                        messages.error(request, f'{field}: {errors}')
        except Exception as e:
            messages.error(request, f'Error de conexión: {str(e)}')
    
    return render(request, 'registration/password_reset_confirm.html', {'token': token})

# Elimina esta línea
# @login_required
def user_dashboard(request):
    """Vista del panel de usuario con transacciones reales"""
    print("\n==== DEBUG USER DASHBOARD ====")
    
    # Verificar autenticación
    if 'access_token' not in request.session or 'user_data' not in request.session:
        print("No hay sesión activa")
        messages.error(request, 'Por favor, inicia sesión para acceder a tu panel.')
        return redirect('login')
    
    # Obtener datos del usuario
    user_data = request.session.get('user_data', {})
    access_token = request.session.get('access_token', '')  # Obtener el token de acceso
    
    # Verificar si es admin
    print(f"Verificando si el usuario es admin: {user_data.get('email')}")
    if user_data.get('email') == 'admin@example.com':
        print("Usuario reconocido como admin, redirigiendo al panel de administrador")
        return redirect('admin_dashboard')
    
    print(f"Datos de usuario: {user_data}")
    
    # Obtener transacciones del usuario
    transactions = []

    try:
        # URL para obtener transacciones del usuario
        url = f"{TRANSACTION_SERVICE_URL}transactions/?sender_id={user_data.get('id')}"
        headers = {'Authorization': f"Bearer {access_token}"}
        
        print(f"Solicitando transacciones a: {url}")
        print(f"Headers: {headers}")
        
        # Realizar la solicitud
        response = requests.get(url, headers=headers)
        
        print(f"Respuesta: {response.status_code}")
        print(f"Contenido: {response.text[:500]}")  # Añadido para debug
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('results', [])
            print(f"Transacciones obtenidas: {len(transactions)}")
        elif response.status_code == 401:
            print("Token inválido o expirado")
            # Intentar refrescar el token
            refresh_token = request.session.get('refresh_token', '')
            if refresh_token:
                try:
                    refresh_response = requests.post(
                        f"{AUTH_SERVICE_URL}token/refresh/",
                        json={"refresh": refresh_token}
                    )
                    if refresh_response.status_code == 200:
                        token_data = refresh_response.json()
                        request.session['access_token'] = token_data.get('access', '')
                        request.session.modified = True
                        # Continuar con el dashboard después de refrescar el token
                        messages.info(request, 'Tu sesión ha sido actualizada.')
                    else:
                        # Si no se pudo refrescar, redirigir a login
                        messages.error(request, 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.')
                        return redirect('login')
                except Exception as refresh_error:
                    print(f"Error al refrescar token: {str(refresh_error)}")
                    messages.error(request, 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.')
                    return redirect('login')
            else:
                # Si no hay token de refresco
                messages.error(request, 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.')
                return redirect('login')
        else:
            print(f"Error al obtener transacciones: {response.status_code}")
            messages.error(request, 'Error al obtener el historial de transacciones.')
    except Exception as e:
        print(f"Excepción al obtener transacciones: {str(e)}")
        messages.error(request, f'Error de conexión: {str(e)}')
        
        
        
        
    
    context = {
        'user_data': user_data,
        'transactions': transactions
    }
    
    return render(request, 'user_panel/dashboard.html', context)

def transaction_form(request):
    """Vista del formulario de transacción con comunicación real"""
    print("\n==== DEBUG TRANSACTION FORM ====")
    
    # Verificar autenticación
    if 'access_token' not in request.session or 'user_data' not in request.session:
        print("No hay sesión activa")
        messages.error(request, 'Por favor, inicia sesión para realizar una transacción.')
        return redirect('login')
    
    # Obtener datos del usuario
    user_data = request.session.get('user_data', {})
    access_token = request.session.get('access_token', '')
    print(f"Datos de usuario: {user_data}")
    
    # Si es POST, procesar el formulario
    if request.method == 'POST':
        print("Procesando formulario POST")
        # Obtener datos del formulario
        receiver_name = request.POST.get('receiver_name')
        amount = request.POST.get('amount')
        message = request.POST.get('message', '')
        
        print(f"Datos de transacción: Receptor={receiver_name}, Monto={amount}, Mensaje={message}")
        
        # Validar datos básicos
        errors = []
        if not receiver_name:
            errors.append('El nombre del destinatario es obligatorio.')
        
        try:
            amount = float(amount)
            if amount <= 0:
                errors.append('El monto debe ser mayor que cero.')
            
            # Verificar saldo suficiente
            user_balance = float(user_data.get('balance', 0))
            if amount > user_balance:
                errors.append('Saldo insuficiente para realizar esta transacción.')
        except (ValueError, TypeError):
            errors.append('El monto debe ser un número válido.')
        
        # Si hay errores, mostrarlos
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'user_panel/transaction_form.html', {'user_data': user_data})
        
        # Si no hay errores, crear la transacción en el microservicio
        try:
            # Preparar datos para la solicitud
            transaction_data = {
                'sender_id': str(user_data.get('id')),
                'sender_name': f"{user_data.get('first_name')} {user_data.get('last_name')}",
                'receiver_name': receiver_name,
                'amount': amount,
                'message': message
            }
            
            # Configurar headers con token JWT
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
            
            # URL del microservicio de transacciones
            url = f"{TRANSACTION_SERVICE_URL}transactions/"
            
            print(f"Enviando solicitud a {url}")
            print(f"Datos: {transaction_data}")
            print(f"Headers: {headers}")
            
            # Realizar la solicitud POST
            response = requests.post(
                url, 
                json=transaction_data,
                headers=headers
            )
            
            print(f"Respuesta: {response.status_code}")
            print(f"Contenido: {response.text[:500]}")
            
            if response.status_code == 201:  # Creado exitosamente
                transaction = response.json()
                
                # Actualizar el saldo del usuario en la sesión
                user_data['balance'] = str(float(user_data.get('balance', 0)) - amount)
                request.session['user_data'] = user_data
                request.session.modified = True
                
                # Mensaje según el estado de la transacción
                if transaction.get('status') == 'fraudulent':
                    messages.warning(request, 'Transacción marcada como posiblemente fraudulenta. Un administrador revisará el caso.')
                else:
                    messages.success(request, 'Transacción realizada con éxito.')
                
                return redirect('user_dashboard')
            else:
                print(f"Error en la creación de la transacción: {response.text}")
                messages.error(request, f'Error al procesar la transacción: {response.status_code}')
                
        except Exception as e:
            print(f"Excepción al crear transacción: {str(e)}")
            messages.error(request, f'Error de conexión: {str(e)}')
    
    # Si es GET, mostrar formulario
    return render(request, 'user_panel/transaction_form.html', {'user_data': user_data})

@login_required
def admin_dashboard(request):
    """Vista del panel de administrador"""
    print("\n==== DEBUG ADMIN DASHBOARD ====")
    print(f"Contenido de la sesión: {dict(request.session)}")
    
    # Verificar autenticación
    if 'access_token' not in request.session or 'user_data' not in request.session:
        print("No hay sesión activa en admin_dashboard")
        messages.error(request, 'Por favor, inicia sesión para acceder al panel de administrador.')
        return redirect('login')
    
    # Obtener datos del usuario
    user_data = request.session.get('user_data', {})
    access_token = request.session.get('access_token', '')
    
    print(f"Email del usuario en admin_dashboard: {user_data.get('email')}")
    
    # Verificar si es admin
    if user_data.get('email') != 'admin@example.com':
        print("Usuario no es admin en admin_dashboard, redirigiendo a user_dashboard")
        messages.error(request, 'Acceso denegado. No tienes permisos de administrador.')
        return redirect('user_dashboard')
    
    print("Usuario verificado como admin, cargando dashboard de administrador")
    
    # Inicializar estructura de estadísticas
    stats = {
        'today': {
            'total': 0,
            'legitimate': 0,
            'possibly_fraudulent': 0,
            'fraudulent': 0,
            'total_amount': 0.0,
        },
        'last_week': {
            'total': 0,
            'legitimate': 0,
            'possibly_fraudulent': 0,
            'fraudulent': 0,
            'total_amount': 0.0,
            'daily_distribution': {},
        },
        'last_month': {
            'total': 0,
            'legitimate': 0,
            'possibly_fraudulent': 0,
            'fraudulent': 0,
            'total_amount': 0.0,
            'daily_distribution': {},
        }
    }
    
    # Obtener estadísticas de transacciones
    headers = {'Authorization': f"Bearer {access_token}"}
    print(f"Headers para solicitud de estadísticas: {headers}")
    
    try:
        # Obtener estadísticas
        stats_url = f"{TRANSACTION_SERVICE_URL}transactions/stats/"
        print(f"Solicitando estadísticas a: {stats_url}")
        
        response = requests.get(stats_url, headers=headers)
        
        print(f"Respuesta de estadísticas: {response.status_code}")
        print(f"Contenido de respuesta estadísticas: {response.text[:500]}")
        
        if response.status_code == 200:
            api_stats = response.json()
            # Actualizar con datos reales si están disponibles
            if api_stats:
                stats.update(api_stats)
        else:
            print(f"Error al obtener estadísticas: {response.status_code}")
            messages.error(request, 'Error al obtener estadísticas')
    except Exception as e:
        print(f"Excepción al obtener estadísticas: {str(e)}")
        messages.error(request, f'Error de conexión: {str(e)}')
    
    # Obtener transacciones fraudulentas para alertas
    fraud_transactions = []
    try:
        fraud_url = f"{TRANSACTION_SERVICE_URL}transactions/?status=fraudulent"
        print(f"Solicitando transacciones fraudulentas a: {fraud_url}")
        
        response = requests.get(fraud_url, headers=headers)
        
        print(f"Respuesta de transacciones fraudulentas: {response.status_code}")
        
        if response.status_code == 200:
            fraud_data = response.json()
            fraud_transactions = fraud_data.get('results', [])
            print(f"Transacciones fraudulentas obtenidas: {len(fraud_transactions)}")
        else:
            print(f"Error al obtener transacciones fraudulentas: {response.status_code}")
    except Exception as e:
        print(f"Excepción al obtener transacciones fraudulentas: {str(e)}")
    
    context = {
        'user_data': user_data,
        'stats': stats,
        'fraud_transactions': fraud_transactions
    }
    
    print("Renderizando template admin_panel/dashboard.html")
    return render(request, 'admin_panel/dashboard.html', context)

@login_required
def admin_transactions(request):
    """Vista de transacciones para el administrador"""
    # Verificar si es admin
 # Verificar autenticación
    if 'access_token' not in request.session or 'user_data' not in request.session:
        print("No hay sesión activa en admin_transactions")
        messages.error(request, 'Por favor, inicia sesión para acceder a las transacciones.')
        return redirect('login')
    
    # Obtener datos del usuario
    user_data = request.session.get('user_data', {})
    access_token = request.session.get('access_token', '')
    
    print(f"Email del usuario en admin_transactions: {user_data.get('email')}")
    
    # Verificar si es admin
    if user_data.get('email') != 'admin@example.com':
        print("Usuario no es admin en admin_transactions, redirigiendo a user_dashboard")
        messages.error(request, 'Acceso denegado. No tienes permisos de administrador.')
        return redirect('user_dashboard')
    
    print("Usuario verificado como admin, cargando transacciones")
    
    # Obtener parámetros de filtro
    status_filter = request.GET.get('status', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    
    # Construir URL con filtros
    url = f"{TRANSACTION_SERVICE_URL}transactions/"
    params = {}
    
    if status_filter:
        params['status'] = status_filter
    if min_amount:
        params['min_amount'] = min_amount
    if max_amount:
        params['max_amount'] = max_amount
    
    # Obtener transacciones
    headers = {'Authorization': f"Bearer {request.session.get('access_token')}"}
    
    try:
        if min_amount or max_amount:
            filter_url = f"{TRANSACTION_SERVICE_URL}transactions/filter_by_amount/"
            response = requests.get(
                filter_url, 
                params=params,
                headers=headers
            )
        else:
            response = requests.get(
                url, 
                params=params,
                headers=headers
            )
        
        if response.status_code == 200:
            if min_amount or max_amount:
                transactions = response.json()
            else:
                transactions = response.json().get('results', [])
        else:
            transactions = []
            messages.error(request, 'Error al obtener transacciones')
    except Exception as e:
        transactions = []
        messages.error(request, f'Error de conexión: {str(e)}')
    
    context = {
        'user_data': user_data,
        'transactions': transactions,
        'status_filter': status_filter,
        'min_amount': min_amount,
        'max_amount': max_amount
    }
    
    return render(request, 'admin_panel/transactions.html', context)

@csrf_exempt
def update_transaction_status(request):
    """Vista para actualizar el estado de una transacción (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        status = data.get('status')
        
        # Actualizar estado
        headers = {'Authorization': f"Bearer {request.session.get('access_token')}"}
        
        try:
            response = requests.post(
                f"{TRANSACTION_SERVICE_URL}transactions/{transaction_id}/update_status/", 
                json={"status": status},
                headers=headers
            )
            
            if response.status_code == 200:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Error al actualizar estado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

# Create your views here.
