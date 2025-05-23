from django.core.management.base import BaseCommand
from transaction_app.models import Transaction
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q

class Command(BaseCommand):
    help = 'Verifica las estadísticas de transacciones para debug'

    def handle(self, *args, **options):
        self.stdout.write('=== VERIFICACIÓN DE ESTADÍSTICAS DE TRANSACCIONES ===\n')
        
        # Obtener fecha actual
        today = timezone.now().date()
        self.stdout.write(f'Fecha actual: {today}\n')
        
        # Total de transacciones
        total_transactions = Transaction.objects.count()
        self.stdout.write(f'Total de transacciones en la BD: {total_transactions}\n')
        
        # Estadísticas de hoy
        self.stdout.write('\n--- ESTADÍSTICAS DE HOY ---')
        today_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time()),
            timezone.get_current_timezone()
        )
        today_end = timezone.make_aware(
            datetime.combine(today, datetime.max.time()),
            timezone.get_current_timezone()
        )
        
        today_transactions = Transaction.objects.filter(
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        
        today_stats = today_transactions.aggregate(
            total=Count('id'),
            total_amount=Sum('amount'),
            legitimate=Count('id', filter=Q(status='legitimate')),
            possibly_fraudulent=Count('id', filter=Q(status='possibly_fraudulent')),
            fraudulent=Count('id', filter=Q(status='fraudulent'))
        )
        
        self.stdout.write(f"Total: {today_stats['total']}")
        self.stdout.write(f"Monto total: ${today_stats['total_amount'] or 0:.2f}")
        self.stdout.write(f"Legítimas: {today_stats['legitimate']}")
        self.stdout.write(f"Posible fraude: {today_stats['possibly_fraudulent']}")
        self.stdout.write(f"Fraudulentas: {today_stats['fraudulent']}")
        
        # Estadísticas de la última semana
        self.stdout.write('\n--- ESTADÍSTICAS DE LA ÚLTIMA SEMANA ---')
        week_start = today - timedelta(days=6)
        week_transactions = Transaction.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=today
        )
        
        week_stats = week_transactions.aggregate(
            total=Count('id'),
            total_amount=Sum('amount')
        )
        
        self.stdout.write(f"Total: {week_stats['total']}")
        self.stdout.write(f"Monto total: ${week_stats['total_amount'] or 0:.2f}")
        
        # Estadísticas del último mes
        self.stdout.write('\n--- ESTADÍSTICAS DEL ÚLTIMO MES ---')
        month_start = today - timedelta(days=29)
        month_transactions = Transaction.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=today
        )
        
        month_stats = month_transactions.aggregate(
            total=Count('id'),
            total_amount=Sum('amount'),
            legitimate=Count('id', filter=Q(status='legitimate')),
            possibly_fraudulent=Count('id', filter=Q(status='possibly_fraudulent')),
            fraudulent=Count('id', filter=Q(status='fraudulent'))
        )
        
        self.stdout.write(f"Total: {month_stats['total']}")
        self.stdout.write(f"Monto total: ${month_stats['total_amount'] or 0:.2f}")
        self.stdout.write(f"Legítimas: {month_stats['legitimate']}")
        self.stdout.write(f"Posible fraude: {month_stats['possibly_fraudulent']}")
        self.stdout.write(f"Fraudulentas: {month_stats['fraudulent']}")
        
        # Distribución diaria del último mes
        self.stdout.write('\n--- DISTRIBUCIÓN DIARIA (ÚLTIMOS 30 DÍAS) ---')
        current_date = month_start
        
        while current_date <= today:
            day_start = timezone.make_aware(
                datetime.combine(current_date, datetime.min.time()),
                timezone.get_current_timezone()
            )
            day_end = timezone.make_aware(
                datetime.combine(current_date, datetime.max.time()),
                timezone.get_current_timezone()
            )
            
            day_count = Transaction.objects.filter(
                created_at__gte=day_start,
                created_at__lte=day_end
            ).count()
            
            if day_count > 0:
                self.stdout.write(f"{current_date.strftime('%Y-%m-%d')}: {day_count} transacciones")
            
            current_date += timedelta(days=1)
        
        # Últimas 5 transacciones
        self.stdout.write('\n--- ÚLTIMAS 5 TRANSACCIONES ---')
        recent_transactions = Transaction.objects.order_by('-created_at')[:5]
        
        for trans in recent_transactions:
            self.stdout.write(
                f"ID: {str(trans.id)[:8]}... | "
                f"Fecha: {trans.created_at.strftime('%Y-%m-%d %H:%M')} | "
                f"Monto: ${trans.amount} | "
                f"Estado: {trans.status}"
            )
        
        self.stdout.write(self.style.SUCCESS('\n=== VERIFICACIÓN COMPLETADA ==='))