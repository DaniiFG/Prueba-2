# fraud_analysis_service/fraud_app/ml_model/model.py
import os
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Ruta al modelo pre-entrenado
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.pkl')

class FraudDetectionModel:
    """Modelo simple de detección de fraude utilizando Random Forest"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.version = 'v1.0'
        self.feature_names = [
            'amount', 'hour_of_day', 'day_of_week', 'is_weekend',
            'sender_avg_amount', 'sender_transaction_count',
            'sender_transaction_frequency', 'amount_deviation'
        ]
        self.load_model()
    
    def load_model(self):
        """Cargar modelo pre-entrenado desde archivo"""
        try:
            if os.path.exists(MODEL_PATH):
                with open(MODEL_PATH, 'rb') as file:
                    saved_model = pickle.load(file)
                    self.model = saved_model['model']
                    self.scaler = saved_model['scaler']
                    self.version = saved_model.get('version', 'v1.0')
                    print(f"Modelo cargado: {self.version}")
            else:
                print("Modelo no encontrado, creando uno nuevo...")
                self._create_default_model()
        except Exception as e:
            print(f"Error al cargar el modelo: {str(e)}")
            self._create_default_model()
    
    def _create_default_model(self):
        """Crear un modelo por defecto si no existe uno pre-entrenado"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        print("Modelo por defecto creado")
    
    def save_model(self):
        """Guardar modelo en archivo"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'version': self.version,
            'feature_names': self.feature_names
        }
        with open(MODEL_PATH, 'wb') as file:
            pickle.dump(model_data, file)
        print(f"Modelo guardado: {self.version}")
    
    def predict(self, features_dict):
        """Predecir si una transacción es fraudulenta"""
        # Convertir diccionario a array numpy
        feature_array = self._prepare_features(features_dict)
        
        # Escalar características
        if self.scaler:
            feature_array = self.scaler.transform([feature_array])[0]
        
        # Predecir probabilidad de fraude
        if hasattr(self.model, 'predict_proba'):
            fraud_proba = self.model.predict_proba([feature_array])[0][1]
        else:
            # Fallback para modelos que no tienen predict_proba
            fraud_proba = float(self.model.predict([feature_array])[0])
        
        # Determinar si es fraude según un umbral
        is_fraud = fraud_proba >= 0.7
        
        # Calcular confianza y factores de riesgo
        confidence = self._calculate_confidence(fraud_proba)
        risk_factors = self._identify_risk_factors(features_dict, feature_array)
        
        return {
            'fraud_score': fraud_proba,
            'is_fraud': is_fraud,
            'confidence': confidence,
            'risk_factors': risk_factors,
            'model_version': self.version
        }
    
    def _prepare_features(self, features_dict):
        """Preparar características para el modelo"""
        feature_array = []
        
        # Extraer características básicas
        feature_array.append(features_dict.get('amount', 0))
        
        # Extraer características temporales
        created_at = features_dict.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        hour_of_day = created_at.hour if created_at else 12
        day_of_week = created_at.weekday() if created_at else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        
        feature_array.append(hour_of_day)
        feature_array.append(day_of_week)
        feature_array.append(is_weekend)
        
        # Características del remitente
        feature_array.append(features_dict.get('sender_avg_amount', 0))
        feature_array.append(features_dict.get('sender_transaction_count', 0))
        feature_array.append(features_dict.get('sender_transaction_frequency', 0))
        
        # Desviación del monto
        avg_amount = features_dict.get('sender_avg_amount', 0)
        amount = features_dict.get('amount', 0)
        amount_deviation = 0
        if avg_amount > 0:
            amount_deviation = (amount - avg_amount) / max(avg_amount, 1)
        feature_array.append(amount_deviation)
        
        return np.array(feature_array)
    
    def _calculate_confidence(self, fraud_proba):
        """Calcular el nivel de confianza de la predicción"""
        # Confianza es alta cuando la probabilidad está cerca de 0 o 1
        return 2 * abs(fraud_proba - 0.5)
    
    def _identify_risk_factors(self, features_dict, feature_array):
        """Identificar factores de riesgo en la transacción"""
        risk_factors = []
        
        # Verificar monto inusual
        amount = features_dict.get('amount', 0)
        avg_amount = features_dict.get('sender_avg_amount', 0)
        
        if avg_amount > 0 and amount > (avg_amount * 3):
            risk_factors.append("Monto significativamente mayor al promedio del usuario")
        
        # Verificar hora inusual
        hour = features_dict.get('created_at').hour if features_dict.get('created_at') else 0
        if hour >= 22 or hour <= 5:
            risk_factors.append("Transacción realizada en horario nocturno")
        
        # Verificar usuario nuevo
        if features_dict.get('sender_transaction_count', 0) <= 1:
            risk_factors.append("Usuario con pocas transacciones previas")
        
        # Verificar fin de semana
        day_of_week = features_dict.get('created_at').weekday() if features_dict.get('created_at') else 0
        if day_of_week >= 5:  # 5=sábado, 6=domingo
            risk_factors.append("Transacción realizada en fin de semana")
        
        return risk_factors

    def train(self, X, y):
        """Entrenar el modelo con nuevos datos"""
        # Escalar características
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Entrenar modelo
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        
        # Actualizar versión
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        self.version = f"v1.{timestamp}"
        
        # Guardar modelo entrenado
        self.save_model()
        
        return {
            'version': self.version,
            'accuracy': self.model.score(X_scaled, y)
        }