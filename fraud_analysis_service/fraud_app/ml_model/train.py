# fraud_analysis_service/fraud_app/ml_model/train.py
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from .model import FraudDetectionModel
from ..models import FraudModel

def generate_synthetic_data(num_samples=100):
    """
    Generar datos sintéticos para entrenamiento inicial.
    Esta función crea datos de ejemplo para entrenar el modelo con características típicas
    de transacciones legítimas y fraudulentas.
    """
    np.random.seed(42)
    
    # Crear arrays para almacenar datos
    amounts = []
    hours = []
    days = []
    is_weekends = []
    avg_amounts = []
    transaction_counts = []
    transaction_frequencies = []
    amount_deviations = []
    is_fraud = []
    
    # Generar datos para transacciones legítimas (70% de los datos)
    for i in range(int(num_samples * 0.7)):
        # Montos típicos (distribución normal alrededor de 100)
        amount = max(10, np.random.normal(100, 50))
        
        # Hora del día (distribución normal alrededor de las 14:00)
        hour = int(np.clip(np.random.normal(14, 4), 0, 23))
        
        # Día de la semana (distribución uniforme, ligeramente menos en fin de semana)
        day = np.random.choice(range(7), p=[0.17, 0.17, 0.17, 0.17, 0.17, 0.08, 0.07])
        is_weekend = 1 if day >= 5 else 0
        
        # Datos del remitente (usuario con historial)
        avg_amount = max(10, np.random.normal(100, 20))
        transaction_count = np.random.randint(5, 50)
        transaction_frequency = np.random.uniform(0.1, 2.0)  # transacciones por día
        
        # Desviación del monto (cercano al promedio para transacciones legítimas)
        amount_deviation = (amount - avg_amount) / max(avg_amount, 1)
        
        # Agregar datos
        amounts.append(amount)
        hours.append(hour)
        days.append(day)
        is_weekends.append(is_weekend)
        avg_amounts.append(avg_amount)
        transaction_counts.append(transaction_count)
        transaction_frequencies.append(transaction_frequency)
        amount_deviations.append(amount_deviation)
        is_fraud.append(0)  # No es fraude
    
    # Generar datos para transacciones fraudulentas (30% de los datos)
    for i in range(int(num_samples * 0.3)):
        # Montos atípicos (o muy pequeños o muy grandes)
        amount_type = np.random.choice(['small', 'large'])
        if amount_type == 'small':
            amount = np.random.uniform(1, 10)
        else:
            amount = np.random.uniform(500, 2000)
        
        # Hora del día (más probable en horas inusuales)
        hour = np.random.choice([np.random.randint(0, 6), np.random.randint(22, 24)])[0]
        
        # Día de la semana (más probable en fin de semana)
        day = np.random.choice(range(7), p=[0.1, 0.1, 0.1, 0.1, 0.1, 0.25, 0.25])
        is_weekend = 1 if day >= 5 else 0
        
        # Datos del remitente (usuario nuevo o con pocas transacciones)
        avg_amount = max(1, np.random.normal(50, 30))
        transaction_count = np.random.randint(0, 5)
        transaction_frequency = np.random.uniform(0, 0.1)  # pocas transacciones por día
        
        # Desviación del monto (muy diferente al promedio para transacciones fraudulentas)
        amount_deviation = (amount - avg_amount) / max(avg_amount, 1)
        
        # Agregar datos
        amounts.append(amount)
        hours.append(hour)
        days.append(day)
        is_weekends.append(is_weekend)
        avg_amounts.append(avg_amount)
        transaction_counts.append(transaction_count)
        transaction_frequencies.append(transaction_frequency)
        amount_deviations.append(amount_deviation)
        is_fraud.append(1)  # Es fraude
    
    # Crear DataFrame
    data = pd.DataFrame({
        'amount': amounts,
        'hour_of_day': hours,
        'day_of_week': days,
        'is_weekend': is_weekends,
        'sender_avg_amount': avg_amounts,
        'sender_transaction_count': transaction_counts,
        'sender_transaction_frequency': transaction_frequencies,
        'amount_deviation': amount_deviations,
        'is_fraud': is_fraud
    })
    
    return data

def train_model(df=None):
    """
    Entrenar el modelo con datos existentes o sintéticos
    """
    # Si no se proporcionan datos, generar datos sintéticos
    if df is None:
        print("Generando datos sintéticos para el entrenamiento...")
        df = generate_synthetic_data(500)  # 500 transacciones de ejemplo
    
    # Preparar datos
    X = df.drop('is_fraud', axis=1).values
    y = df['is_fraud'].values
    
    # Dividir en conjuntos de entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Crear y entrenar modelo
    model = FraudDetectionModel()
    result = model.train(X_train, y_train)
    
    # Evaluar modelo
    scaler = model.scaler
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.model.predict(X_test_scaled)
    y_pred_proba = model.model.predict_proba(X_test_scaled)[:, 1]
    
    # Calcular métricas
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"Modelo entrenado: {result['version']}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print(f"AUC: {auc:.4f}")
    
    # Guardar métricas del modelo en la base de datos
    features_used = model.feature_names
    
    # Crear entrada en la base de datos
    try:
        model_entry = FraudModel.objects.create(
            version=result['version'],
            description="Modelo entrenado con datos sintéticos",
            features_used=features_used,
            model_file=model.MODEL_PATH,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc=auc,
            is_active=True
        )
        
        # Desactivar modelos anteriores
        FraudModel.objects.exclude(id=model_entry.id).update(is_active=False)
        
        print(f"Modelo guardado en la base de datos: {model_entry}")
    except Exception as e:
        print(f"Error al guardar modelo en la base de datos: {str(e)}")
    
    return {
        'version': result['version'],
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'auc': auc
    }

if __name__ == "__main__":
    print("Iniciando entrenamiento del modelo...")
    train_model()