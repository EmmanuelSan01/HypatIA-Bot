"""
Middleware y herramientas de monitoreo de latencia para el chatbot
"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class LatencyMonitor:
    """Monitor de latencia para diferentes componentes del chatbot"""
    
    def __init__(self, max_samples: int = 1000):
        self._max_samples = max_samples
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._start_times: Dict[str, float] = {}
        self._component_stats: Dict[str, Dict] = defaultdict(dict)
        
    def start_timing(self, component: str, operation: str = "default") -> str:
        """Inicia el timing para un componente/operación"""
        timing_key = f"{component}:{operation}"
        self._start_times[timing_key] = time.time()
        return timing_key
    
    def end_timing(self, timing_key: str) -> float:
        """Finaliza el timing y registra la latencia"""
        if timing_key not in self._start_times:
            logger.warning(f"Timing key no encontrado: {timing_key}")
            return 0.0
        
        latency = time.time() - self._start_times[timing_key]
        del self._start_times[timing_key]
        
        # Registrar la latencia
        self._metrics[timing_key].append({
            'latency': latency,
            'timestamp': datetime.now().isoformat()
        })
        
        # Actualizar estadísticas
        self._update_component_stats(timing_key, latency)
        
        # Log si la latencia es alta
        if latency > 2.0:  # Más de 2 segundos
            component, operation = timing_key.split(':', 1)
            logger.warning(f"⚠️  Latencia alta detectada: {component}.{operation} = {latency:.3f}s")
        
        return latency
    
    def _update_component_stats(self, timing_key: str, latency: float):
        """Actualiza estadísticas del componente"""
        if timing_key not in self._component_stats:
            self._component_stats[timing_key] = {
                'total_calls': 0,
                'total_time': 0,
                'avg_latency': 0,
                'min_latency': float('inf'),
                'max_latency': 0,
                'p95_latency': 0,
                'p99_latency': 0
            }
        
        stats = self._component_stats[timing_key]
        stats['total_calls'] += 1
        stats['total_time'] += latency
        stats['avg_latency'] = stats['total_time'] / stats['total_calls']
        stats['min_latency'] = min(stats['min_latency'], latency)
        stats['max_latency'] = max(stats['max_latency'], latency)
        
        # Calcular percentiles
        latencies = [m['latency'] for m in self._metrics[timing_key]]
        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            stats['p95_latency'] = sorted_latencies[int(0.95 * n)] if n > 0 else 0
            stats['p99_latency'] = sorted_latencies[int(0.99 * n)] if n > 0 else 0
    
    def get_component_stats(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene estadísticas de un componente específico o todos"""
        if component:
            return {k: v for k, v in self._component_stats.items() if k.startswith(component)}
        return dict(self._component_stats)
    
    def get_slow_operations(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """Obtiene operaciones que superan el threshold de latencia"""
        slow_ops = []
        
        for timing_key, stats in self._component_stats.items():
            if stats['avg_latency'] > threshold:
                component, operation = timing_key.split(':', 1)
                slow_ops.append({
                    'component': component,
                    'operation': operation,
                    'avg_latency': stats['avg_latency'],
                    'max_latency': stats['max_latency'],
                    'total_calls': stats['total_calls'],
                    'p99_latency': stats['p99_latency']
                })
        
        return sorted(slow_ops, key=lambda x: x['avg_latency'], reverse=True)
    
    def get_recent_metrics(self, component: str, minutes: int = 5) -> List[Dict[str, Any]]:
        """Obtiene métricas recientes de un componente"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = []
        
        for timing_key in self._metrics:
            if timing_key.startswith(component):
                for metric in self._metrics[timing_key]:
                    metric_time = datetime.fromisoformat(metric['timestamp'])
                    if metric_time >= cutoff_time:
                        recent_metrics.append({
                            'timing_key': timing_key,
                            **metric
                        })
        
        return sorted(recent_metrics, key=lambda x: x['timestamp'])
    
    def generate_latency_report(self) -> Dict[str, Any]:
        """Genera un reporte completo de latencia"""
        total_operations = sum(stats['total_calls'] for stats in self._component_stats.values())
        
        report = {
            'summary': {
                'total_operations': total_operations,
                'components_monitored': len(set(k.split(':')[0] for k in self._component_stats.keys())),
                'monitoring_period': 'since_startup',
                'report_timestamp': datetime.now().isoformat()
            },
            'component_stats': self.get_component_stats(),
            'slow_operations': self.get_slow_operations(),
            'performance_alerts': self._generate_performance_alerts()
        }
        
        return report
    
    def _generate_performance_alerts(self) -> List[Dict[str, Any]]:
        """Genera alertas de rendimiento"""
        alerts = []
        
        # Alerta por operaciones muy lentas
        for timing_key, stats in self._component_stats.items():
            component, operation = timing_key.split(':', 1)
            
            if stats['avg_latency'] > 3.0:
                alerts.append({
                    'type': 'high_average_latency',
                    'component': component,
                    'operation': operation,
                    'severity': 'high',
                    'message': f"Latencia promedio muy alta: {stats['avg_latency']:.3f}s",
                    'recommendations': [
                        'Revisar implementación del componente',
                        'Considerar cacheo adicional',
                        'Verificar conexiones de base de datos'
                    ]
                })
            
            if stats['p99_latency'] > 5.0:
                alerts.append({
                    'type': 'high_p99_latency',
                    'component': component,
                    'operation': operation,
                    'severity': 'medium',
                    'message': f"P99 latencia alta: {stats['p99_latency']:.3f}s",
                    'recommendations': [
                        'Investigar casos extremos',
                        'Optimizar consultas pesadas'
                    ]
                })
        
        return alerts
    
    def reset_metrics(self):
        """Reinicia todas las métricas"""
        self._metrics.clear()
        self._component_stats.clear()
        self._start_times.clear()
        logger.info("Métricas de latencia reiniciadas")

# Instancia global del monitor
latency_monitor = LatencyMonitor()

class TimingContext:
    """Context manager para medir automáticamente la latencia"""
    
    def __init__(self, component: str, operation: str = "default"):
        self.component = component
        self.operation = operation
        self.timing_key = None
        self.latency = 0.0
    
    def __enter__(self):
        self.timing_key = latency_monitor.start_timing(self.component, self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timing_key:
            self.latency = latency_monitor.end_timing(self.timing_key)

def measure_latency(component: str, operation: str = "default"):
    """Decorator para medir latencia de funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TimingContext(component, operation) as timing:
                result = func(*args, **kwargs)
                
            # Log si es necesario
            if timing.latency > 1.0:
                logger.info(f"⏱️  {component}.{operation}: {timing.latency:.3f}s")
            
            return result
        return wrapper
    return decorator

# Función de utilidad para medición manual
def time_operation(component: str, operation: str = "default"):
    """Función de utilidad para crear un context manager de timing"""
    return TimingContext(component, operation)
