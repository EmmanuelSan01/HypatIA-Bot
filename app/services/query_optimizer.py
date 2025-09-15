"""
Optimizador de consultas SQL y conexiones para mejorar rendimiento
"""
import logging
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimizador de consultas SQL con connection pooling y cacheo"""
    
    def __init__(self):
        self._query_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutos
        self._query_stats: Dict[str, Dict] = {}
    
    def get_optimized_curso_query(self, incremental: bool = False, since_date: Optional[str] = None) -> str:
        """Consulta optimizada para cursos con índices mejorados"""
        base_query = """
        SELECT 
            c.id, c.titulo, c.descripcion, c.precio, c.cupo, 
            c.nivel, c.idioma, c.categoriaId,
            cat.nombre as categoria_nombre,
            -- Optimización: usar COALESCE para manejar NULLs
            COALESCE(GROUP_CONCAT(
                DISTINCT CONCAT(pr.descripcion, ':', pr.descuentoPorcentaje, '%') 
                SEPARATOR ' | '
            ), '') as promociones_activas
        FROM curso c 
        -- Usar INNER JOIN en lugar de LEFT JOIN para categoría (asumiendo que siempre existe)
        INNER JOIN categoria cat ON c.categoriaId = cat.id
        -- LEFT JOIN optimizado con filtros en la condición de JOIN
        LEFT JOIN promocionCurso pc ON c.id = pc.cursoId
        LEFT JOIN promocion pr ON pc.promocionId = pr.id 
            AND pr.fechaInicio <= CURDATE() 
            AND pr.fechaFin >= CURDATE()
        """
        
        if incremental and since_date:
            base_query += f" WHERE c.fechaActualizacion >= '{since_date}'"
        
        base_query += """
        GROUP BY c.id, c.titulo, c.descripcion, c.precio, c.cupo, 
                 c.nivel, c.idioma, c.categoriaId, cat.nombre
        -- Índice sugerido: CREATE INDEX idx_curso_fecha_actualizacion ON curso(fechaActualizacion)
        """
        
        return base_query
    
    def get_optimized_promocion_query(self, active_only: bool = True) -> str:
        """Consulta optimizada para promociones"""
        query = """
        SELECT 
            pr.id, pr.descripcion, pr.descuentoPorcentaje, 
            pr.fechaInicio, pr.fechaFin,
            -- Optimización: calcular counts sin subconsultas
            COUNT(DISTINCT c.id) as total_cursos,
            COALESCE(GROUP_CONCAT(DISTINCT c.titulo SEPARATOR ', '), '') as cursos_nombres,
            COALESCE(GROUP_CONCAT(
                DISTINCT CONCAT(c.titulo, ' ($', c.precio, ')') 
                SEPARATOR ', '
            ), '') as cursos_detalles
        FROM promocion pr
        LEFT JOIN promocionCurso pc ON pr.id = pc.promocionId
        LEFT JOIN curso c ON pc.cursoId = c.id
        """
        
        if active_only:
            query += " WHERE pr.fechaInicio <= CURDATE() AND pr.fechaFin >= CURDATE()"
        
        query += """
        GROUP BY pr.id, pr.descripcion, pr.descuentoPorcentaje, 
                 pr.fechaInicio, pr.fechaFin
        -- Índices sugeridos: 
        -- CREATE INDEX idx_promocion_fechas ON promocion(fechaInicio, fechaFin)
        -- CREATE INDEX idx_promocion_curso ON promocionCurso(promocionId, cursoId)
        """
        
        return query
    
    def measure_query_performance(self, query_name: str):
        """Decorator para medir el rendimiento de consultas"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Registrar estadísticas
                if query_name not in self._query_stats:
                    self._query_stats[query_name] = {
                        'total_executions': 0,
                        'total_time': 0,
                        'avg_time': 0,
                        'min_time': float('inf'),
                        'max_time': 0
                    }
                
                stats = self._query_stats[query_name]
                stats['total_executions'] += 1
                stats['total_time'] += execution_time
                stats['avg_time'] = stats['total_time'] / stats['total_executions']
                stats['min_time'] = min(stats['min_time'], execution_time)
                stats['max_time'] = max(stats['max_time'], execution_time)
                
                logger.info(f"Query {query_name} ejecutada en {execution_time:.3f}s")
                
                # Alertar si la consulta es muy lenta
                if execution_time > 2.0:  # Más de 2 segundos
                    logger.warning(f"⚠️  Query lenta detectada: {query_name} ({execution_time:.3f}s)")
                
                return result
            return wrapper
        return decorator
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de rendimiento de consultas"""
        return {
            "query_statistics": self._query_stats.copy(),
            "cache_size": len(self._query_cache),
            "total_queries_tracked": len(self._query_stats)
        }
    
    def suggest_indexes(self) -> List[str]:
        """Sugiere índices para mejorar el rendimiento"""
        return [
            "CREATE INDEX idx_curso_categoria ON curso(categoriaId);",
            "CREATE INDEX idx_curso_fecha_actualizacion ON curso(fechaActualizacion);",
            "CREATE INDEX idx_curso_disponible_cupo ON curso(cupo) WHERE cupo > 0;",
            "CREATE INDEX idx_promocion_fechas ON promocion(fechaInicio, fechaFin);",
            "CREATE INDEX idx_promocion_activa ON promocion(fechaInicio, fechaFin) WHERE fechaInicio <= CURDATE() AND fechaFin >= CURDATE();",
            "CREATE INDEX idx_promocion_curso_composite ON promocionCurso(promocionId, cursoId);",
            "CREATE INDEX idx_categoria_nombre ON categoria(nombre);"
        ]

# Instancia global del optimizador
query_optimizer = QueryOptimizer()
