from django.core.management.base import BaseCommand
from frontend_app.utils import debug_microservices_status, check_database_connections

class Command(BaseCommand):
    help = 'Debug del estado del dashboard y microservicios'

    def handle(self, *args, **options):
        self.stdout.write('=== DEBUG DEL DASHBOARD ===\n')
        
        # Verificar estado de microservicios
        self.stdout.write('1. Estado de Microservicios:')
        services_status = debug_microservices_status()
        
        for service, status in services_status.items():
            status_color = self.style.SUCCESS if 'UP' in status['status'] else self.style.ERROR
            self.stdout.write(f"   {service}: {status_color(status['status'])} - {status['url']}")
        
        # Verificar conexiones de base de datos
        self.stdout.write('\n2. Estado de Bases de Datos:')
        db_status = check_database_connections()
        
        for db, status in db_status.items():
            self.stdout.write(f"   {db}: {status['status']}")
            if 'total_transactions' in status:
                self.stdout.write(f"      Total transacciones: {status['total_transactions']}")
        
        # Sugerencias
        self.stdout.write('\n3. Sugerencias para resolver problemas:')
        
        if any('DOWN' in status['status'] for status in services_status.values()):
            self.stdout.write(self.style.WARNING('   - Algunos microservicios están inactivos. Inicia todos los servicios:'))
            self.stdout.write('     python manage.py runserver 8001  # auth_service')
            self.stdout.write('     python manage.py runserver 8002  # transaction_service') 
            self.stdout.write('     python manage.py runserver 8003  # fraud_analysis_service')
            self.stdout.write('     python manage.py runserver 8000  # frontend')
        
        transaction_count = 0
        if 'transactions_db' in db_status:
            transaction_count = db_status['transactions_db'].get('total_transactions', 0)
        
        if transaction_count == 0:
            self.stdout.write(self.style.WARNING('   - No hay transacciones en la base de datos. Genera datos de prueba:'))
            self.stdout.write('     cd transaction_service')
            self.stdout.write('     python manage.py generate_test_transactions --count 50')
        
        self.stdout.write('\n4. URLs importantes:')
        self.stdout.write('   - Frontend: http://localhost:8000')
        self.stdout.write('   - Admin Dashboard: http://localhost:8000/admin-panel/dashboard/')
        self.stdout.write('   - Login con: admin@example.com')
        
        self.stdout.write(self.style.SUCCESS('\n=== FIN DEL DEBUG ==='))