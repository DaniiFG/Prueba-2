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
        self.is_trained = False
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
                    self.is_trained = True
                    print(f"Modelo cargado: {self.version}")
            else:
                print("Modelo no encontrado, creando uno nuevo...")
                self._create_and_train_default_model()
        except Exception as e:
            print(f"Error al cargar el modelo: {str(e)}")
            self._create_and_train_default_model()
    
    def _create_and_train_default_model(self):
        """Crear y entrenar un modelo por defecto con datos sintéticos"""
        try:
            print("Creando modelo por defecto con datos sintéticos...")
            
            # Generar datos sintéticos para entrenamiento inicial
            X_train, y_train = self._generate_synthetic_training_data()
            
            # Crear modelo y scaler
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.scaler = StandardScaler()
            
            # Entrenar
            X_train_scaled = self.scaler.fit_transform(X_train)
            self.model.fit(X_train_scaled, y_train)
            
            self.is_trained = True
            
            # Guardar modelo
            self.save_model()
            
            print("Modelo por defecto creado y entrenado exitosamente")
            
        except Exception as e:
            print(f"Error al crear modelo por defecto: {str(e)}")
            # Crear modelo básico sin entrenar como último recurso
            self.model = RandomForestClassifier(n_estimators=10, random_state=42)
            self.scaler = StandardScaler()
            self.is_trained = False
    
    def _generate_synthetic_training_data(self, n_samples=1000):
        """Generar datos sintéticos para entrenamiento"""
        np.random.seed(42)
        
        X = []
        y = []
        
        # Generar transacciones legítimas (70%)
        n_legitimate = int(n_samples * 0.7)
        for _ in range(n_legitimate):
            # Características típicas de transacciones legítimas
            amount = max(10, np.random.normal(150, 75))  # Montos normales
            hour_of_day = np.random.choice(range(8, 22), p=[0.05, 0.05, 0.1, 0.15, 0.15, 0.15, 0.15, 0.1, 0.05, 0.03, 0.02, 0.02, 0.01, 0.01])  # Horas laborales
            day_of_week = np.random.randint(0, 7)
            is_weekend = 1 if day_of_week >= 5 else 0
            sender_avg_amount = max(10, np.random.normal(130, 40))
            sender_transaction_count = np.random.randint(5, 100)
            sender_transaction_frequency = np.random.uniform(0.1, 3.0)
            amount_deviation = (amount - sender_avg_amount) / max(sender_avg_amount, 1)
            
            X.append([amount, hour_of_day, day_of_week, is_weekend, 
                     sender_avg_amount, sender_transaction_count, 
                     sender_transaction_frequency, amount_deviation])
            y.append(0)  # No fraude
        
        # Generar transacciones fraudulentas (30%)
        n_fraudulent = n_samples - n_legitimate
        for _ in range(n_fraudulent):
            # Características típicas de transacciones fraudulentas
            amount_type = np.random.choice(['very_small', 'very_large'])
            if amount_type == 'very_small':
                amount = np.random.uniform(1, 15)
            else:
                amount = np.random.uniform(500, 5000)
            
            # Horas inusuales
            hour_of_day = np.random.choice([0, 1, 2, 3, 4, 5, 22, 23])
            day_of_week = np.random.randint(0, 7)
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # Usuario con poco historial
            sender_avg_amount = max(1, np.random.normal(80, 50))
            sender_transaction_count = np.random.randint(0, 8)
            sender_transaction_frequency = np.random.uniform(0, 0.2)
            amount_deviation = (amount - sender_avg_amount) / max(sender_avg_amount, 1)
            
            X.append([amount, hour_of_day, day_of_week, is_weekend, 
                     sender_avg_amount, sender_transaction_count, 
                     sender_transaction_frequency, amount_deviation])
            y.append(1)  # Fraude
        
        return np.array(X), np.array(y)
    
    def save_model(self):
        """Guardar modelo en archivo"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'version': self.version,
                'feature_names': self.feature_names
            }
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            
            with open(MODEL_PATH, 'wb') as file:
                pickle.dump(model_data, file)
            print(f"Modelo guardado: {self.version}")
        except Exception as e:
            print(f"Error al guardar modelo: {str(e)}")
    
    def predict(self, features_dict):
        """Predecir si una transacción es fraudulenta"""
        try:
            # Preparar características
            feature_array = self._prepare_features(features_dict)
            
            # Si el modelo no está entrenado, usar reglas simples
            if not self.is_trained:
                return self._rule_based_prediction(features_dict, feature_array)
            
            # Escalar características
            feature_array_scaled = self.scaler.transform([feature_array])
            
            # Predecir probabilidad de fraude
            if hasattr(self.model, 'predict_proba'):
                fraud_proba = self.model.predict_proba(feature_array_scaled)[0][1]
            else:
                fraud_proba = float(self.model.predict(feature_array_scaled)[0])
            
            # Determinar si es fraude según un umbral
            is_fraud = fraud_proba >= 0.7
            
            # Calcular confianza y factores de riesgo
            confidence = self._calculate_confidence(fraud_proba)
            risk_factors = self._identify_risk_factors(features_dict, feature_array)
            
            return {
                'fraud_score': float(fraud_proba),
                'is_fraud': bool(is_fraud),
                'confidence': float(confidence),
                'risk_factors': risk_factors,
                'model_version': self.version
            }
            
        except Exception as e:
            print(f"Error en predicción: {str(e)}")
            # Retornar predicción por defecto en caso de error
            return {
                'fraud_score': 0.1,
                'is_fraud': False,
                'confidence': 0.9,
                'risk_factors': [f"Error en análisis: {str(e)}"],
                'model_version': 'error'
            }
    
    def _rule_based_prediction(self, features_dict, feature_array):
        """Predicción basada en reglas cuando el modelo no está disponible"""
        risk_score = 0.0
        risk_factors = []
        
        amount = features_dict.get('amount', 0)
        created_at = features_dict.get('created_at')
        
        # Regla 1: Montos inusuales
        if amount > 1000:
            risk_score += 0.3
            risk_factors.append("Monto alto (>$1000)")
        elif amount < 5:
            risk_score += 0.2
            risk_factors.append("Monto muy bajo (<$5)")
        
        # Regla 2: Horario inusual
        if created_at:
            hour = created_at.hour if hasattr(created_at, 'hour') else 12
            if hour < 6 or hour > 22:
                risk_score += 0.3
                risk_factors.append("Transacción en horario inusual")
        
        # Regla 3: Usuario nuevo
        sender_transaction_count = features_dict.get('sender_transaction_count', 0)
        if sender_transaction_count < 3:
            risk_score += 0.2
            risk_factors.append("Usuario con pocas transacciones previas")
        
        # Regla 4: Desviación del monto promedio
        sender_avg_amount = features_dict.get('sender_avg_amount', 0)
        if sender_avg_amount > 0 and amount > (sender_avg_amount * 5):
            risk_score += 0.4
            risk_factors.append("Monto significativamente mayor al promedio del usuario")
        
        # Limitar score entre 0 y 1
        fraud_score = min(risk_score, 1.0)
        is_fraud = fraud_score >= 0.7
        confidence = 0.8 if len(risk_factors) > 2 else 0.6
        
        return {
            'fraud_score': fraud_score,
            'is_fraud': is_fraud,
            'confidence': confidence,
            'risk_factors': risk_factors,
            'model_version': 'rules_v1.0'
        }
    
    def _prepare_features(self, features_dict):
        """Preparar características para el modelo"""
        feature_array = []
        
        # Extraer características básicas
        feature_array.append(float(features_dict.get('amount', 0)))
        
        # Extraer características temporales
        created_at = features_dict.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()
        
        hour_of_day = created_at.hour if hasattr(created_at, 'hour') else 12
        day_of_week = created_at.weekday() if hasattr(created_at, 'weekday') else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        
        feature_array.append(hour_of_day)
        feature_array.append(day_of_week)
        feature_array.append(is_weekend)
        
        # Características del remitente
        feature_array.append(float(features_dict.get('sender_avg_amount', 0)))
        feature_array.append(int(features_dict.get('sender_transaction_count', 0)))
        feature_array.append(float(features_dict.get('sender_transaction_frequency', 0)))
        
        # Desviación del monto
        avg_amount = float(features_dict.get('sender_avg_amount', 0))
        amount = float(features_dict.get('amount', 0))
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
        elif amount > 1000:
            risk_factors.append("Monto alto de transacción")
        elif amount < 5:
            risk_factors.append("Monto inusualmente bajo")
        
        # Verificar hora inusual
        created_at = features_dict.get('created_at')
        if created_at:
            hour = created_at.hour if hasattr(created_at, 'hour') else 12
            if hour >= 22 or hour <= 5:
                risk_factors.append("Transacción realizada en horario nocturno")
        
        # Verificar usuario nuevo
        if features_dict.get('sender_transaction_count', 0) <= 2:
            risk_factors.append("Usuario con pocas transacciones previas")
        
        # Verificar fin de semana
        if created_at and hasattr(created_at, 'weekday'):
            day_of_week = created_at.weekday()
            if day_of_week >= 5:  # 5=sábado, 6=domingo
                risk_factors.append("Transacción realizada en fin de semana")
        
        # Verificar frecuencia baja de transacciones
        if features_dict.get('sender_transaction_frequency', 0) < 0.1:
            risk_factors.append("Usuario con baja frecuencia de transacciones")
        
        return risk_factors

    def train(self, X, y):
        """Entrenar el modelo con nuevos datos"""
        try:
            print(f"Entrenando modelo con {X.shape[0]} muestras...")
            
            # Verificar y limpiar datos
            if np.isnan(X).any():
                print("⚠️ Limpiando valores NaN en X...")
                X = np.nan_to_num(X, nan=0.0)
            
            if np.isnan(y).any():
                print("⚠️ Limpiando valores NaN en y...")
                y = np.nan_to_num(y, nan=0)
            
            # Escalar características
            print("Escalando características...")
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Entrenar modelo
            print("Entrenando Random Forest...")
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1  # Usar todos los cores disponibles
            )
            self.model.fit(X_scaled, y)
            
            # Actualizar versión
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            self.version = f"v1.{timestamp}"
            self.is_trained = True
            
            print(f"Modelo entrenado exitosamente. Versión: {self.version}")
            
            # Guardar modelo entrenado
            self.save_model()
            
            # Calcular accuracy en el conjunto de entrenamiento
            train_accuracy = self.model.score(X_scaled, y)
            
            return {
                'version': self.version,
                'accuracy': float(train_accuracy)
            }
            
        except Exception as e:
            print(f"❌ Error al entrenar modelo: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'version': 'error',
                'accuracy': 0.0
            }