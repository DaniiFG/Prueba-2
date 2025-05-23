from django.core.management.base import BaseCommand
from fraud_app.models import TransactionFeature, UserActivityProfile
from datetime import datetime, timedelta
import random
import uuid
from django.db import models

class Command(BaseCommand):
    help = 'Genera características de transacciones para el análisis de fraude'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Número de características a generar'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(f'Generando {count} características de transacciones...')
        
        created_count = 0
        
        for i in range(count):
            try:
                # Generar datos aleatorios para las características
                transaction_id = str(uuid.uuid4())
                sender_id = str(random.randint(1, 20))
                amount = round(random.uniform(1.0, 5000.0), 2)
                
                # Fecha aleatoria en los últimos 30 días
                days_back = random.randint(0, 30)
                created_at = datetime.now() - timedelta(days=days_back)
                
                hour_of_day = created_at.hour
                day_of_week = created_at.weekday()
                is_weekend = day_of_week >= 5
                
                # Características del remitente (simuladas)
                sender_avg_amount = round(random.uniform(50.0, 300.0), 2)
                sender_transaction_count = random.randint(1, 50)
                sender_transaction_frequency = round(random.uniform(0.1, 3.0), 2)
                amount_deviation = (amount - sender_avg_amount) / max(sender_avg_amount, 1)
                
                # Determinar si es fraude basado en ciertas reglas
                is_fraud = False
                fraud_score = 0.1
                
                # Reglas para determinar fraude
                if amount > 2000:  # Monto muy alto
                    fraud_score += 0.3
                if amount < 5:  # Monto muy bajo
                    fraud_score += 0.2
                if hour_of_day < 6 or hour_of_day > 22:  # Hora inusual
                    fraud_score += 0.3
                if sender_transaction_count < 3:  # Usuario nuevo
                    fraud_score += 0.2
                if abs(amount_deviation) > 3:  # Desviación alta
                    fraud_score += 0.4
                
                fraud_score = min(fraud_score, 1.0)
                is_fraud = fraud_score > 0.7
                
                # Crear la característica
                feature = TransactionFeature.objects.create(
                    transaction_id=transaction_id,
                    sender_id=sender_id,
                    amount=amount,
                    created_at=created_at,
                    hour_of_day=hour_of_day,
                    day_of_week=day_of_week,
                    is_weekend=is_weekend,
                    sender_avg_amount=sender_avg_amount,
                    sender_transaction_count=sender_transaction_count,
                    sender_transaction_frequency=sender_transaction_frequency,
                    amount_deviation=amount_deviation,
                    fraud_score=fraud_score,
                    is_fraud=is_fraud,
                    model_version='test_v1.0'
                )
                
                created_count += 1
                
                if created_count % 20 == 0:
                    self.stdout.write(f'Creadas {created_count} características...')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creando característica {i+1}: {str(e)}')
                )
                continue
        
        # Generar algunos perfiles de usuario
        self.stdout.write('Generando perfiles de usuario...')
        
        for user_id in range(1, 21):
            try:
                user_transactions = TransactionFeature.objects.filter(sender_id=str(user_id))
                
                if user_transactions.exists():
                    amounts = [t.amount for t in user_transactions]
                    
                    profile, created = UserActivityProfile.objects.get_or_create(
                        user_id=str(user_id),
                        defaults={
                            'avg_transaction_amount': sum(amounts) / len(amounts),
                            'max_transaction_amount': max(amounts),
                            'min_transaction_amount': min(amounts),
                            'total_transactions': len(amounts),
                            'fraudulent_transactions': user_transactions.filter(is_fraud=True).count(),
                            'common_transaction_hours': [12, 14, 16],
                            'common_transaction_days': [0, 1, 2, 3, 4]
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'Perfil creado para usuario {user_id}')
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creando perfil para usuario {user_id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'¡Completado! Se crearon {created_count} características de transacciones.')
        )
        
        # Mostrar resumen
        total_features = TransactionFeature.objects.count()
        fraud_features = TransactionFeature.objects.filter(is_fraud=True).count()
        high_risk_features = TransactionFeature.objects.filter(fraud_score__gte=0.5).count()
        
        self.stdout.write('\n--- RESUMEN DE CARACTERÍSTICAS ---')
        self.stdout.write(f'Total de características: {total_features}')
        self.stdout.write(f'Marcadas como fraude: {fraud_features}')
        self.stdout.write(f'Alto riesgo (score >= 0.5): {high_risk_features}')
        
        avg_score = TransactionFeature.objects.aggregate(
            avg_score=models.Avg('fraud_score')
        )['avg_score'] or 0
        
        self.stdout.write(f'Score promedio de fraude: {avg_score:.3f}')
        
        profiles_count = UserActivityProfile.objects.count()
        self.stdout.write(f'Perfiles de usuario creados: {profiles_count}')