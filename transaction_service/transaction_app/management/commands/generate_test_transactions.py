from django.core.management.base import BaseCommand
from transaction_app.models import Transaction
from datetime import datetime, timedelta
import random
import uuid

class Command(BaseCommand):
    help = 'Genera transacciones de prueba para testing del dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Número de transacciones a generar'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de días hacia atrás para generar transacciones'
        )

    def handle(self, *args, **options):
        count = options['count']
        days = options['days']
        
        self.stdout.write(f'Generando {count} transacciones de prueba para los últimos {days} días...')
        
        # Listas de nombres ficticios
        sender_names = [
            'Juan Pérez', 'María García', 'Carlos López', 'Ana Martínez', 'Luis Rodríguez',
            'Carmen Fernández', 'José González', 'Laura Sánchez', 'Miguel Torres', 'Elena Ruiz'
        ]
        
        receiver_names = [
            'Pedro Jiménez', 'Sofía Herrera', 'Diego Morales', 'Valentina Castro', 'Andrés Ortiz',
            'Isabella Vargas', 'Mateo Ramírez', 'Camila Flores', 'Santiago Méndez', 'Gabriela Cruz'
        ]
        
        # Estados posibles con probabilidades
        statuses = [
            ('legitimate', 0.7),  # 70% legítimas
            ('possibly_fraudulent', 0.2),  # 20% posiblemente fraudulentas
            ('fraudulent', 0.1)  # 10% fraudulentas
        ]
        
        created_count = 0
        
        for i in range(count):
            try:
                # Generar fecha aleatoria en los últimos 'days' días
                days_back = random.randint(0, days)
                hours_back = random.randint(0, 23)
                minutes_back = random.randint(0, 59)
                
                created_at = datetime.now() - timedelta(
                    days=days_back, 
                    hours=hours_back, 
                    minutes=minutes_back
                )
                
                # Seleccionar estado basado en probabilidades
                rand = random.random()
                cumulative_prob = 0
                selected_status = 'legitimate'
                
                for status, prob in statuses:
                    cumulative_prob += prob
                    if rand <= cumulative_prob:
                        selected_status = status
                        break
                
                # Generar monto basado en el estado
                if selected_status == 'legitimate':
                    amount = round(random.uniform(10.0, 500.0), 2)
                elif selected_status == 'possibly_fraudulent':
                    # Montos más altos o muy bajos para posible fraude
                    if random.random() < 0.5:
                        amount = round(random.uniform(1.0, 5.0), 2)  # Muy bajo
                    else:
                        amount = round(random.uniform(1000.0, 3000.0), 2)  # Muy alto
                else:  # fraudulent
                    # Montos extremos para fraude
                    if random.random() < 0.3:
                        amount = round(random.uniform(0.01, 1.0), 2)  # Extremadamente bajo
                    else:
                        amount = round(random.uniform(5000.0, 10000.0), 2)  # Extremadamente alto
                
                # Generar score de fraude basado en el estado
                if selected_status == 'legitimate':
                    fraud_score = random.uniform(0.0, 0.3)
                elif selected_status == 'possibly_fraudulent':
                    fraud_score = random.uniform(0.4, 0.7)
                else:  # fraudulent
                    fraud_score = random.uniform(0.7, 1.0)
                
                # Crear transacción
                transaction = Transaction.objects.create(
                    sender_id=str(random.randint(1, 20)),  # IDs de usuario ficticios
                    sender_name=random.choice(sender_names),
                    receiver_name=random.choice(receiver_names),
                    amount=amount,
                    message=f'Transacción de prueba #{i+1}',
                    status=selected_status,
                    fraud_score=fraud_score,
                    created_at=created_at
                )
                
                created_count += 1
                
                if created_count % 10 == 0:
                    self.stdout.write(f'Creadas {created_count} transacciones...')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creando transacción {i+1}: {str(e)}')
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'¡Completado! Se crearon {created_count} transacciones de prueba.')
        )
        
        # Mostrar resumen
        total_transactions = Transaction.objects.count()
        legitimate_count = Transaction.objects.filter(status='legitimate').count()
        possibly_fraudulent_count = Transaction.objects.filter(status='possibly_fraudulent').count()
        fraudulent_count = Transaction.objects.filter(status='fraudulent').count()
        
        self.stdout.write('\n--- RESUMEN DE TRANSACCIONES ---')
        self.stdout.write(f'Total de transacciones en BD: {total_transactions}')
        self.stdout.write(f'Legítimas: {legitimate_count}')
        self.stdout.write(f'Posiblemente fraudulentas: {possibly_fraudulent_count}')
        self.stdout.write(f'Fraudulentas: {fraudulent_count}')
        
        # Mostrar distribución por días
        from django.utils import timezone
        today = timezone.now().date()
        
        today_count = Transaction.objects.filter(created_at__date=today).count()
        week_count = Transaction.objects.filter(
            created_at__date__gte=today - timedelta(days=7)
        ).count()
        month_count = Transaction.objects.filter(
            created_at__date__gte=today - timedelta(days=30)
        ).count()
        
        self.stdout.write('\n--- DISTRIBUCIÓN TEMPORAL ---')
        self.stdout.write(f'Transacciones hoy: {today_count}')
        self.stdout.write(f'Transacciones última semana: {week_count}')
        self.stdout.write(f'Transacciones último mes: {month_count}')
        
        self.stdout.write(
            self.style.SUCCESS('\n¡Listo! Ahora puedes ver estadísticas en el dashboard de administrador.')
        )