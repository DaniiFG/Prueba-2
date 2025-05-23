# fraud_analysis_service/fraud_app/ml_model/train.py
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from .model import FraudDetectionModel
from ..models import FraudModel

def generate_synthetic_data(num_samples=1000):
    """
    Generar datos sintéticos para entrenamiento inicial.
    """
    np.random.seed(42)
    
    # Listas para almacenar datos
    data = []
    
    print(f"Generando {num_samples} muestras sintéticas...")
    
    # Generar datos para transacciones legítimas (70% de los datos)
    n_legitimate = int(num_samples * 0.7)
    print(f"Generando {n_legitimate} transacciones legítimas...")
    
    for i in range(n_legitimate):
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
        data.append({
            'amount': amount,
            'hour_of_day': hour,
            'day_of_week': day,
            'is_weekend': is_weekend,
            'sender_avg_amount': avg_amount,
            'sender_transaction_count': transaction_count,
            'sender_transaction_frequency': transaction_frequency,
            'amount_deviation': amount_deviation,
            'is_fraud': 0  # No es fraude
        })
    
    # Generar datos para transacciones fraudulentas (30% de los datos)
    n_fraudulent = num_samples - n_legitimate
    print(f"Generando {n_fraudulent} transacciones fraudulentas...")
    
    for i in range(n_fraudulent):
        # Montos atípicos (o muy pequeños o muy grandes)
        amount_type = np.random.choice(['small', 'large'])
        if amount_type == 'small':
            amount = np.random.uniform(1, 10)
        else:
            amount = np.random.uniform(500, 2000)
        
        # Horas inusuales
        unusual_hours = [0, 1, 2, 3, 4, 5, 22, 23]
        hour = np.random.choice(unusual_hours)
        
        # Día de la semana (más probable en fin de semana)
        day = np.random.choice(range(7), p=[0.1, 0.1, 0.1, 0.1, 0.1, 0.25, 0.25])
        is_weekend = 1 if day >= 5 else 0
        
        # Usuario con poco historial
        avg_amount = max(1, np.random.normal(50, 30))
        transaction_count = np.random.randint(0, 5)
        transaction_frequency = np.random.uniform(0, 0.1)  # pocas transacciones por día
        
        # Desviación del monto (muy diferente al promedio para transacciones fraudulentas)
        amount_deviation = (amount - avg_amount) / max(avg_amount, 1)
        
        # Agregar datos
        data.append({
            'amount': amount,
            'hour_of_day': hour,
            'day_of_week': day,
            'is_weekend': is_weekend,
            'sender_avg_amount': avg_amount,
            'sender_transaction_count': transaction_count,
            'sender_transaction_frequency': transaction_frequency,
            'amount_deviation': amount_deviation,
            'is_fraud': 1  # Es fraude
        })
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    print(f"DataFrame creado con {len(df)} filas y {len(df.columns)} columnas")
    
    return df

def train_model(df=None):
    """
    Entrenar el modelo con datos existentes o sintéticos
    """
    try:
        print("Iniciando proceso de entrenamiento...")
        
        # Si no se proporcionan datos, generar datos sintéticos
        if df is None:
            print("No se proporcionaron datos, generando datos sintéticos...")
            df = generate_synthetic_data(1000)  # 1000 transacciones de ejemplo
        
        print(f"Datos para entrenamiento: {len(df)} muestras")
        print(f"Distribución de clases:")
        print(f"- Legítimas: {len(df[df['is_fraud'] == 0])}")
        print(f"- Fraudulentas: {len(df[df['is_fraud'] == 1])}")
        
        # Preparar datos
        feature_columns = ['amount', 'hour_of_day', 'day_of_week', 'is_weekend',
                          'sender_avg_amount', 'sender_transaction_count',
                          'sender_transaction_frequency', 'amount_deviation']
        
        X = df[feature_columns].values
        y = df['is_fraud'].values
        
        print(f"Forma de X: {X.shape}")
        print(f"Forma de y: {y.shape}")
        
        # Verificar que no hay valores NaN
        if np.isnan(X).any():
            print("⚠️ Advertencia: Se encontraron valores NaN en X, reemplazando con 0")
            X = np.nan_to_num(X, nan=0.0)
        
        if np.isnan(y).any():
            print("⚠️ Advertencia: Se encontraron valores NaN en y, reemplazando con 0")
            y = np.nan_to_num(y, nan=0)
        
        # Dividir en conjuntos de entrenamiento y prueba
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"Conjunto de entrenamiento: {X_train.shape[0]} muestras")
        print(f"Conjunto de prueba: {X_test.shape[0]} muestras")
        
        # Crear y entrenar modelo
        print("Creando modelo de detección de fraude...")
        model = FraudDetectionModel()
        result = model.train(X_train, y_train)
        
        print(f"Entrenamiento completado. Versión del modelo: {result['version']}")
        
        # Evaluar modelo
        print("Evaluando modelo en conjunto de prueba...")
        
        # Realizar predicciones
        scaler = model.scaler
        X_test_scaled = scaler.transform(X_test)
        y_pred = model.model.predict(X_test_scaled)
        
        # Verificar que el modelo tiene predict_proba
        if hasattr(model.model, 'predict_proba'):
            y_pred_proba = model.model.predict_proba(X_test_scaled)[:, 1]
        else:
            y_pred_proba = y_pred.astype(float)
        
        # Calcular métricas
        accuracy = accuracy_score(y_test, y_pred)
        
        # Usar zero_division=0 para evitar warnings
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # Calcular AUC solo si hay ambas clases
        if len(np.unique(y_test)) > 1:
            auc = roc_auc_score(y_test, y_pred_proba)
        else:
            auc = 0.5
        
        print(f"Métricas de evaluación:")
        print(f"- Accuracy: {accuracy:.4f}")
        print(f"- Precision: {precision:.4f}")
        print(f"- Recall: {recall:.4f}")
        print(f"- F1 Score: {f1:.4f}")
        print(f"- AUC: {auc:.4f}")
        
        # Guardar métricas del modelo en la base de datos
        features_used = model.feature_names
        
        # Crear entrada en la base de datos
        try:
            print("Guardando información del modelo en la base de datos...")
            model_entry = FraudModel.objects.create(
                version=result['version'],
                description="Modelo entrenado con datos sintéticos",
                features_used=features_used,
                model_file=model.MODEL_PATH if hasattr(model, 'MODEL_PATH') else 'model.pkl',
                accuracy=float(accuracy),
                precision=float(precision),
                recall=float(recall),
                f1_score=float(f1),
                auc=float(auc),
                is_active=True
            )
            
            # Desactivar modelos anteriores
            FraudModel.objects.exclude(id=model_entry.id).update(is_active=False)
            
            print(f"✅ Modelo guardado en la base de datos: {model_entry}")
        except Exception as e:
            print(f"⚠️ Error al guardar modelo en la base de datos: {str(e)}")
            print("El modelo se entrenó correctamente, pero no se pudo guardar en BD")
        
        return {
            'version': result['version'],
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'auc': float(auc)
        }
        
    except Exception as e:
        print(f"❌ Error durante el entrenamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    print("Iniciando entrenamiento del modelo...")
    result = train_model()
    print("Entrenamiento completado exitosamente!")
    print(f"Métricas finales: {result}")