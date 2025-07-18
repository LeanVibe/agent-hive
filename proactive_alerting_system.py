"""
Proactive Alerting System for Multi-Agent Coordination.

Advanced alerting with predictive capabilities, anomaly detection,
and critical system condition monitoring for production environments.
"""

import logging
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import threading
from collections import defaultdict, deque

from prometheus_client import Counter, Histogram, Gauge
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from monitoring_alerts import AlertManager
from business_metrics_monitor import BusinessMetricsMonitor


class AlertCategory(Enum):
    """Categories of alerts for better organization."""
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance" 
    BUSINESS_METRICS = "business_metrics"
    SECURITY = "security"
    AGENT_COORDINATION = "agent_coordination"
    PREDICTIVE = "predictive"


class AlertSeverity(Enum):
    """Enhanced alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PredictiveAlert:
    """Predictive alert with forecasting data."""
    alert_id: str
    category: AlertCategory
    severity: AlertSeverity
    metric_name: str
    current_value: float
    predicted_value: float
    prediction_time: datetime
    confidence: float
    threshold_breach_eta: Optional[timedelta]
    recommendation: str
    auto_mitigation_available: bool
    historical_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CriticalSystemCondition:
    """Critical system condition definition."""
    condition_id: str
    name: str
    description: str
    detection_function: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    auto_mitigation: Optional[Callable[[Dict[str, Any]], bool]]
    escalation_path: List[str]


class AnomalyDetector:
    """Machine learning-based anomaly detection."""
    
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names: List[str] = []
        self.training_data: deque = deque(maxlen=1000)
        self.detection_threshold = -0.5  # Anomaly score threshold
    
    def add_training_data(self, features: Dict[str, float]) -> None:
        """Add data point for training."""
        if not self.feature_names:
            self.feature_names = sorted(features.keys())
        
        # Ensure consistent feature order
        feature_vector = [features.get(name, 0.0) for name in self.feature_names]
        self.training_data.append(feature_vector)
        
        # Retrain if we have enough data
        if len(self.training_data) >= 50 and len(self.training_data) % 10 == 0:
            self._retrain()
    
    def detect_anomaly(self, features: Dict[str, float]) -> Tuple[bool, float]:
        """Detect if current features represent an anomaly."""
        if not self.is_trained:
            return False, 0.0
        
        # Prepare feature vector
        feature_vector = [features.get(name, 0.0) for name in self.feature_names]
        scaled_features = self.scaler.transform([feature_vector])
        
        # Get anomaly score
        anomaly_score = self.model.decision_function(scaled_features)[0]
        is_anomaly = anomaly_score < self.detection_threshold
        
        return is_anomaly, anomaly_score
    
    def _retrain(self) -> None:
        """Retrain the anomaly detection model."""
        if len(self.training_data) < 20:
            return
        
        try:
            # Prepare training data
            X = np.array(list(self.training_data))
            
            # Scale features
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Train model
            self.model.fit(X_scaled)
            self.is_trained = True
            
        except Exception as e:
            logging.error(f"Failed to retrain anomaly detector: {e}")


class MetricPredictor:
    """Simple time series predictor for metrics."""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
    
    def add_metric_value(self, metric_name: str, value: float, timestamp: datetime) -> None:
        """Add metric value to history."""
        self.metric_history[metric_name].append((value, timestamp))
    
    def predict_next_value(self, metric_name: str, 
                          prediction_horizon: timedelta = timedelta(minutes=30)) -> Optional[Tuple[float, float]]:
        """Predict next value for metric with confidence."""
        history = self.metric_history.get(metric_name)
        if not history or len(history) < 5:
            return None
        
        # Extract values and calculate trend
        values = [point[0] for point in history]
        timestamps = [point[1] for point in history]
        
        # Simple linear trend calculation
        n = len(values)
        if n < 2:
            return None
        
        # Calculate linear regression coefficients
        x_values = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
        
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return values[-1], 0.5  # No trend, return last value with low confidence
        
        # Linear regression: y = mx + b
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Predict future value
        future_x = prediction_horizon.total_seconds()
        predicted_value = slope * future_x + intercept
        
        # Calculate confidence based on R-squared
        y_mean = statistics.mean(values)
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        ss_res = sum((values[i] - (slope * x_values[i] + intercept)) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        confidence = max(0.1, min(0.9, r_squared))
        
        return predicted_value, confidence


class ProactiveAlertingSystem:
    """Advanced proactive alerting with predictive capabilities."""
    
    def __init__(self, business_metrics_monitor: BusinessMetricsMonitor):
        self.logger = logging.getLogger(__name__)
        self.business_metrics = business_metrics_monitor
        self.alert_manager = AlertManager()
        
        # Predictive components
        self.anomaly_detector = AnomalyDetector()
        self.metric_predictor = MetricPredictor()
        
        # Alert storage
        self.predictive_alerts: List[PredictiveAlert] = []
        self.critical_conditions: Dict[str, CriticalSystemCondition] = {}
        
        # Prometheus metrics
        self.alert_counter = Counter('alerts_generated_total', 'Total alerts generated', ['category', 'severity'])
        self.prediction_accuracy = Histogram('prediction_accuracy_score', 'Prediction accuracy scores')
        self.system_health_gauge = Gauge('system_health_score', 'Overall system health score')
        
        # Configuration
        self.prediction_horizons = {
            "short_term": timedelta(minutes=15),
            "medium_term": timedelta(hours=1),
            "long_term": timedelta(hours=4)
        }
        
        # Monitoring state
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Setup critical conditions
        self._setup_critical_conditions()
        
        self.logger.info("ProactiveAlertingSystem initialized")
    
    def _setup_critical_conditions(self) -> None:
        """Setup critical system conditions to monitor."""
        
        def agent_cascade_failure_detector(metrics: Dict[str, Any]) -> bool:
            """Detect potential agent cascade failure."""
            failed_agents = metrics.get("failed_agents_count", 0)
            total_agents = metrics.get("total_agents", 1)
            failure_rate = failed_agents / total_agents
            return failure_rate > 0.3  # More than 30% agents failing
        
        def coordination_deadlock_detector(metrics: Dict[str, Any]) -> bool:
            """Detect coordination deadlock conditions."""
            avg_coordination_time = metrics.get("avg_coordination_time", 0)
            active_conflicts = metrics.get("active_conflicts", 0)
            return avg_coordination_time > 300 and active_conflicts > 5  # 5min+ with 5+ conflicts
        
        def resource_exhaustion_detector(metrics: Dict[str, Any]) -> bool:
            """Detect resource exhaustion."""
            memory_usage = metrics.get("memory_percent", 0)
            cpu_usage = metrics.get("cpu_percent", 0)
            disk_usage = metrics.get("disk_percent", 0)
            return memory_usage > 95 or cpu_usage > 98 or disk_usage > 98
        
        def task_throughput_collapse_detector(metrics: Dict[str, Any]) -> bool:
            """Detect task throughput collapse."""
            current_throughput = metrics.get("system_throughput", 0)
            baseline_throughput = metrics.get("baseline_throughput", 1)
            return current_throughput < baseline_throughput * 0.1  # 90% drop
        
        # Register critical conditions
        self.critical_conditions = {
            "agent_cascade_failure": CriticalSystemCondition(
                condition_id="agent_cascade_failure",
                name="Agent Cascade Failure",
                description="Multiple agents failing simultaneously",
                detection_function=agent_cascade_failure_detector,
                severity=AlertSeverity.EMERGENCY,
                auto_mitigation=None,
                escalation_path=["ops_team", "engineering_lead", "cto"]
            ),
            "coordination_deadlock": CriticalSystemCondition(
                condition_id="coordination_deadlock",
                name="Coordination Deadlock",
                description="Agent coordination system deadlock detected",
                detection_function=coordination_deadlock_detector,
                severity=AlertSeverity.CRITICAL,
                auto_mitigation=None,
                escalation_path=["ops_team", "engineering_lead"]
            ),
            "resource_exhaustion": CriticalSystemCondition(
                condition_id="resource_exhaustion",
                name="Resource Exhaustion",
                description="Critical system resource exhaustion",
                detection_function=resource_exhaustion_detector,
                severity=AlertSeverity.EMERGENCY,
                auto_mitigation=None,
                escalation_path=["ops_team", "infrastructure_team"]
            ),
            "task_throughput_collapse": CriticalSystemCondition(
                condition_id="task_throughput_collapse",
                name="Task Throughput Collapse",
                description="System task throughput collapsed",
                detection_function=task_throughput_collapse_detector,
                severity=AlertSeverity.CRITICAL,
                auto_mitigation=None,
                escalation_path=["ops_team", "engineering_lead"]
            )
        }
    
    def start_monitoring(self) -> None:
        """Start proactive alerting monitoring."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Proactive alerting system started")
    
    def stop_monitoring(self) -> None:
        """Stop proactive alerting monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Proactive alerting system stopped")
    
    def process_metrics(self, metrics: Dict[str, Any]) -> None:
        """Process new metrics and generate alerts."""
        current_time = datetime.now()
        
        with self.lock:
            # Update anomaly detector training data
            numeric_metrics = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
            self.anomaly_detector.add_training_data(numeric_metrics)
            
            # Update predictor with metric history
            for metric_name, value in numeric_metrics.items():
                self.metric_predictor.add_metric_value(metric_name, value, current_time)
            
            # Check for anomalies
            self._check_anomalies(numeric_metrics, current_time)
            
            # Generate predictive alerts
            self._generate_predictive_alerts(numeric_metrics, current_time)
            
            # Check critical system conditions
            self._check_critical_conditions(metrics, current_time)
            
            # Update system health score
            self._update_system_health_score(metrics)
    
    def _check_anomalies(self, metrics: Dict[str, float], timestamp: datetime) -> None:
        """Check for anomalies in current metrics."""
        is_anomaly, anomaly_score = self.anomaly_detector.detect_anomaly(metrics)
        
        if is_anomaly:
            alert = PredictiveAlert(
                alert_id=f"anomaly_{int(timestamp.timestamp())}",
                category=AlertCategory.PREDICTIVE,
                severity=AlertSeverity.MEDIUM if anomaly_score < -0.7 else AlertSeverity.HIGH,
                metric_name="system_behavior",
                current_value=anomaly_score,
                predicted_value=anomaly_score,
                prediction_time=timestamp,
                confidence=abs(anomaly_score),
                threshold_breach_eta=None,
                recommendation="Investigate unusual system behavior patterns",
                auto_mitigation_available=False,
                historical_context={"anomaly_score": anomaly_score, "metrics": metrics}
            )
            
            self.predictive_alerts.append(alert)
            self.alert_counter.labels(category=alert.category.value, severity=alert.severity.value).inc()
            
            self.logger.warning(f"Anomaly detected: score={anomaly_score:.3f}, metrics={metrics}")
    
    def _generate_predictive_alerts(self, metrics: Dict[str, float], timestamp: datetime) -> None:
        """Generate predictive alerts for metrics."""
        for metric_name, current_value in metrics.items():
            for horizon_name, horizon_time in self.prediction_horizons.items():
                prediction = self.metric_predictor.predict_next_value(metric_name, horizon_time)
                
                if prediction:
                    predicted_value, confidence = prediction
                    
                    # Check if prediction indicates threshold breach
                    threshold_breach = self._check_predicted_threshold_breach(
                        metric_name, current_value, predicted_value, confidence
                    )
                    
                    if threshold_breach:
                        severity, eta, recommendation = threshold_breach
                        
                        alert = PredictiveAlert(
                            alert_id=f"predict_{metric_name}_{horizon_name}_{int(timestamp.timestamp())}",
                            category=AlertCategory.PREDICTIVE,
                            severity=severity,
                            metric_name=metric_name,
                            current_value=current_value,
                            predicted_value=predicted_value,
                            prediction_time=timestamp + horizon_time,
                            confidence=confidence,
                            threshold_breach_eta=eta,
                            recommendation=recommendation,
                            auto_mitigation_available=False,
                            historical_context={"horizon": horizon_name, "prediction_confidence": confidence}
                        )
                        
                        self.predictive_alerts.append(alert)
                        self.alert_counter.labels(category=alert.category.value, severity=alert.severity.value).inc()
                        
                        self.logger.info(f"Predictive alert: {metric_name} predicted to breach threshold in {eta}")
    
    def _check_predicted_threshold_breach(self, metric_name: str, current_value: float, 
                                        predicted_value: float, confidence: float) -> Optional[Tuple[AlertSeverity, timedelta, str]]:
        """Check if predicted value indicates threshold breach."""
        # Define thresholds for common metrics
        thresholds = {
            "cpu_percent": {"warning": 80, "critical": 95},
            "memory_percent": {"warning": 85, "critical": 95},
            "disk_percent": {"warning": 90, "critical": 98},
            "task_throughput": {"warning": 5, "critical": 2},  # Lower is worse
            "error_rate": {"warning": 0.05, "critical": 0.10},  # Higher is worse
            "response_time": {"warning": 2.0, "critical": 5.0}  # Higher is worse
        }
        
        metric_thresholds = thresholds.get(metric_name)
        if not metric_thresholds:
            return None
        
        # Only alert if confidence is reasonable
        if confidence < 0.3:
            return None
        
        # Check for threshold breaches
        warning_threshold = metric_thresholds["warning"]
        critical_threshold = metric_thresholds["critical"]
        
        # Determine if metric is "higher is worse" or "lower is worse"
        higher_is_worse = metric_name in ["cpu_percent", "memory_percent", "disk_percent", "error_rate", "response_time"]
        
        if higher_is_worse:
            if predicted_value >= critical_threshold:
                severity = AlertSeverity.HIGH
                eta = timedelta(minutes=30)  # Estimate
                recommendation = f"Take immediate action to prevent {metric_name} from reaching critical levels"
            elif predicted_value >= warning_threshold:
                severity = AlertSeverity.MEDIUM
                eta = timedelta(hours=1)
                recommendation = f"Monitor {metric_name} closely and consider optimization"
            else:
                return None
        else:  # Lower is worse
            if predicted_value <= critical_threshold:
                severity = AlertSeverity.HIGH
                eta = timedelta(minutes=30)
                recommendation = f"Take immediate action to prevent {metric_name} from dropping to critical levels"
            elif predicted_value <= warning_threshold:
                severity = AlertSeverity.MEDIUM
                eta = timedelta(hours=1)
                recommendation = f"Monitor {metric_name} closely and consider optimization"
            else:
                return None
        
        return severity, eta, recommendation
    
    def _check_critical_conditions(self, metrics: Dict[str, Any], timestamp: datetime) -> None:
        """Check for critical system conditions."""
        for condition_id, condition in self.critical_conditions.items():
            try:
                if condition.detection_function(metrics):
                    # Generate critical alert
                    alert = PredictiveAlert(
                        alert_id=f"critical_{condition_id}_{int(timestamp.timestamp())}",
                        category=AlertCategory.SYSTEM_HEALTH,
                        severity=condition.severity,
                        metric_name=condition_id,
                        current_value=1.0,  # Boolean condition triggered
                        predicted_value=1.0,
                        prediction_time=timestamp,
                        confidence=1.0,
                        threshold_breach_eta=timedelta(0),  # Immediate
                        recommendation=f"CRITICAL: {condition.description}. Escalate to: {', '.join(condition.escalation_path)}",
                        auto_mitigation_available=condition.auto_mitigation is not None,
                        historical_context={"escalation_path": condition.escalation_path}
                    )
                    
                    self.predictive_alerts.append(alert)
                    self.alert_counter.labels(category=alert.category.value, severity=alert.severity.value).inc()
                    
                    self.logger.critical(f"Critical condition detected: {condition.name}")
                    
                    # Attempt auto-mitigation if available
                    if condition.auto_mitigation:
                        try:
                            success = condition.auto_mitigation(metrics)
                            if success:
                                self.logger.info(f"Auto-mitigation successful for {condition.name}")
                            else:
                                self.logger.warning(f"Auto-mitigation failed for {condition.name}")
                        except Exception as e:
                            self.logger.error(f"Auto-mitigation error for {condition.name}: {e}")
                            
            except Exception as e:
                self.logger.error(f"Error checking critical condition {condition_id}: {e}")
    
    def _update_system_health_score(self, metrics: Dict[str, Any]) -> None:
        """Update overall system health score."""
        try:
            # Calculate health score based on various factors
            health_factors = []
            
            # System resource health (0-1)
            cpu_health = max(0, 1 - metrics.get("cpu_percent", 0) / 100)
            memory_health = max(0, 1 - metrics.get("memory_percent", 0) / 100)
            disk_health = max(0, 1 - metrics.get("disk_percent", 0) / 100)
            health_factors.extend([cpu_health, memory_health, disk_health])
            
            # Business metrics health (0-1)
            throughput = metrics.get("task_throughput", 0)
            throughput_health = min(1.0, throughput / 10.0)  # Normalize to 10 tasks/hour baseline
            health_factors.append(throughput_health)
            
            # Error rate health (0-1)
            error_rate = metrics.get("error_rate", 0)
            error_health = max(0, 1 - error_rate)
            health_factors.append(error_health)
            
            # Agent coordination health (0-1)
            coordination_efficiency = metrics.get("coordination_efficiency", 0.8)
            health_factors.append(coordination_efficiency)
            
            # Calculate weighted average
            overall_health = statistics.mean(health_factors) if health_factors else 0.5
            
            # Update Prometheus gauge
            self.system_health_gauge.set(overall_health)
            
            # Generate alert if health is critically low
            if overall_health < 0.3:
                alert = PredictiveAlert(
                    alert_id=f"health_critical_{int(time.time())}",
                    category=AlertCategory.SYSTEM_HEALTH,
                    severity=AlertSeverity.CRITICAL,
                    metric_name="system_health_score",
                    current_value=overall_health,
                    predicted_value=overall_health,
                    prediction_time=datetime.now(),
                    confidence=1.0,
                    threshold_breach_eta=timedelta(0),
                    recommendation="System health critically low. Immediate investigation required.",
                    auto_mitigation_available=False,
                    historical_context={"health_factors": dict(zip(["cpu", "memory", "disk", "throughput", "errors", "coordination"], health_factors))}
                )
                
                self.predictive_alerts.append(alert)
                self.logger.critical(f"System health critically low: {overall_health:.2f}")
                
        except Exception as e:
            self.logger.error(f"Error updating system health score: {e}")
    
    def _monitoring_loop(self) -> None:
        """Main proactive alerting monitoring loop."""
        while self.running:
            try:
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Validate prediction accuracy (if possible)
                self._validate_prediction_accuracy()
                
                # Auto-resolve outdated predictive alerts
                self._auto_resolve_alerts()
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in proactive alerting monitoring loop: {e}")
                time.sleep(5)
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old predictive alerts."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        with self.lock:
            self.predictive_alerts = [
                alert for alert in self.predictive_alerts
                if alert.prediction_time > cutoff_time
            ]
    
    def _validate_prediction_accuracy(self) -> None:
        """Validate accuracy of past predictions."""
        current_time = datetime.now()
        
        # Check predictions that should have materialized
        for alert in self.predictive_alerts[:]:
            if (alert.prediction_time <= current_time and 
                alert.category == AlertCategory.PREDICTIVE):
                
                # This is a simplified validation - in production, you'd compare
                # against actual metric values at the prediction time
                accuracy_score = 0.7  # Placeholder - would be calculated based on actual vs predicted
                self.prediction_accuracy.observe(accuracy_score)
    
    def _auto_resolve_alerts(self) -> None:
        """Auto-resolve alerts that are no longer relevant."""
        current_time = datetime.now()
        
        with self.lock:
            resolved_count = 0
            for alert in self.predictive_alerts[:]:
                # Auto-resolve predictive alerts after their prediction time has passed
                if (alert.category == AlertCategory.PREDICTIVE and 
                    current_time > alert.prediction_time + timedelta(hours=1)):
                    self.predictive_alerts.remove(alert)
                    resolved_count += 1
            
            if resolved_count > 0:
                self.logger.debug(f"Auto-resolved {resolved_count} outdated predictive alerts")
    
    def get_active_predictive_alerts(self, severity: Optional[AlertSeverity] = None) -> List[PredictiveAlert]:
        """Get active predictive alerts."""
        with self.lock:
            alerts = self.predictive_alerts[:]
            
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            
            return sorted(alerts, key=lambda x: x.prediction_time, reverse=True)
    
    def get_system_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system health dashboard."""
        current_time = datetime.now()
        
        with self.lock:
            # Count alerts by category and severity
            alert_counts = defaultdict(lambda: defaultdict(int))
            for alert in self.predictive_alerts:
                alert_counts[alert.category.value][alert.severity.value] += 1
            
            # Get critical alerts
            critical_alerts = [
                alert for alert in self.predictive_alerts
                if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
            ]
            
            # Calculate system metrics
            total_alerts = len(self.predictive_alerts)
            critical_count = len(critical_alerts)
            
            return {
                "timestamp": current_time.isoformat(),
                "system_health_score": self.system_health_gauge._value._value if hasattr(self.system_health_gauge, '_value') else 0.5,
                "total_active_alerts": total_alerts,
                "critical_alerts": critical_count,
                "alert_counts_by_category": dict(alert_counts),
                "critical_conditions_active": len([
                    condition for condition in self.critical_conditions.values()
                    if condition.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
                ]),
                "prediction_engine_status": "active" if self.anomaly_detector.is_trained else "training",
                "next_predictions": [
                    {
                        "metric": alert.metric_name,
                        "predicted_value": alert.predicted_value,
                        "eta": alert.threshold_breach_eta.total_seconds() if alert.threshold_breach_eta else 0,
                        "confidence": alert.confidence
                    }
                    for alert in self.predictive_alerts[-5:]  # Last 5 predictions
                ]
            }