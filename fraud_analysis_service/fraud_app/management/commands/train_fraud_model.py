# fraud_analysis_service/fraud_app/management/commands/train_fraud_model.py
from django.core.management.base import BaseCommand
from fraud_app.ml_model.train import train_model
import os

class Command(BaseCommand):
    help = 'Entrena el modelo de detección de fraude con datos sintéticos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples',
            type=int,
            default=1000,
            help='Número de muestras sintéticas a generar'
        )

    def handle(self, *args, **options):
        self.stdout.write('Iniciando entrenamiento del modelo de fraude...')
        
        try:
            # Crear directorio para el modelo si no existe
            from fraud_app.ml_model.model import MODEL_PATH
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            
            # Entrenar modelo
            result = train_model()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Modelo entrenado exitosamente!\n'
                    f'Versión: {result["version"]}\n'
                    f'Accuracy: {result["accuracy"]:.4f}\n'
                    f'Precision: {result["precision"]:.4f}\n'
                    f'Recall: {result["recall"]:.4f}\n'
                    f'F1 Score: {result["f1_score"]:.4f}\n'
                    f'AUC: {result["auc"]:.4f}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al entrenar el modelo: {str(e)}')
            )