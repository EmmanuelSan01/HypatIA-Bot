"""
Agent.py - Migración completa a Langroid Framework
BaekhoBot: Asistente comercial especializado en productos de Taekwondo
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Langroid imports
from langroid.agent.base import Agent
from langroid.agent.task import Task
from langroid.agent.config import ChatAgentConfig
from langroid.language_models.config import LLMConfig
from langroid.vector_stores.config import QdrantConfig
from langroid.vector_stores.qdrant_db import QdrantDB
from langroid.embedding_models.config import EmbeddingConfig
from langroid.embedding_models.models import EmbeddingModel
from langroid.agent.tools.vector_search_tool import VectorSearchTool

from app.config import Config

logger = logging.getLogger(__name__)

# ==============================
# SISTEMA DE ESTADO CONVERSACIONAL
# ==============================

class ConversationPhase(Enum):
    GREETING = "greeting"
    NEEDS_ASSESSMENT = "needs_assessment"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    PRICE_DISCUSSION = "price_discussion"
    SIZE_FITTING = "size_fitting"
    CLOSING = "closing"

class UserLevel(Enum):
    BEGINNER = "principiante"
    INTERMEDIATE = "intermedio"
    ADVANCED = "avanzado"
    COMPETITOR = "competidor"
    INSTRUCTOR = "instructor"

@dataclass
class State:
    """Estado conversacional optimizado"""
    user_id: str
    name: Optional[str] = None
    level: Optional[UserLevel] = None
    budget_range: Optional[str] = None
    phase: ConversationPhase = ConversationPhase.GREETING
    was_greeted: bool = False
    history_messages: List[str] = None
    identified_needs: List[str] = None
    interested_categories: List[str] = None
    last_activity: datetime = None
    message_count: int = 0
    context: str = ""
    summary: Optional[str] = None
    
    def __post_init__(self):
        if self.history_messages is None:
            self.history_messages = []
        if self.identified_needs is None:
            self.identified_needs = []
        if self.interested_categories is None:
            self.interested_categories = []
        if self.last_activity is None:
            self.last_activity = datetime.now()

# ==============================
# CONFIGURACIONES LANGROID
# ==============================

def get_llm_config() -> LLMConfig:
    """Configuración optimizada del LLM"""
    return LLMConfig(
        type="openai",
        chat_model="gpt-4o-mini",
        chat_context_length=8000,
        max_output_tokens=400,  # Respuestas concisas
        temperature=0.3,
        timeout=20,
        api_key=Config.OPENAI_API_KEY
    )

def get_qdrant_config() -> QdrantConfig:
    """Configuración de Qdrant para RAG"""
    return QdrantConfig(
        host=getattr(Config, 'QDRANT_HOST', 'localhost'),
        port=getattr(Config, 'QDRANT_PORT', 6333),
        api_key=getattr(Config, 'QDRANT_API_KEY', None),
        collection_name="productos_taekwondo"
    )

def get_embedding_config() -> EmbeddingConfig:
    """Configuración de embeddings"""
    return EmbeddingConfig(
        model_type="openai",
        model_name="text-embedding-ada-002",
        api_key=Config.OPENAI_API_KEY
    )

# ==============================
# PROMPT OPTIMIZADO ESTRUCTURA
# ==============================

def build_prompt(state: State) -> str:
    """Construye el prompt principal con estado del usuario"""
    nombre = state.name or "❓ Cliente"
    nivel = state.level.value if state.level else "❓ No especificado"
    presupuesto = state.budget_range or "❓ No proporcionado"
    saludo_estado = "✅ Ya saludado" if state.was_greeted else "❌ Pendiente saludo"
    historial = " | ".join(state.history_messages[-3:]) if state.history_messages else "❓ Sin historial"
    necesidades = ", ".join(state.identified_needs) if state.identified_needs else "❓ Por identificar"
    categorias = ", ".join(state.interested_categories) if state.interested_categories else "❓ No especificadas"
    
    resumen_usuario = f"""
📌 *Resumen del usuario*:
- Nombre: {nombre}
- Nivel: {nivel}
- Presupuesto: {presupuesto}
- Context: {state.context}
- Historial: {historial}
- ¿Ya saludado?: {saludo_estado}
- Necesidades: {necesidades}
- Categorías interés: {categorias}
- Fase actual: {state.phase.value}
- Total mensajes: {state.message_count}
"""

    historial_context = f"\n🕑 *Historial de Interacciones:*\n{historial}" if historial != "❓ Sin historial" else ""

    return f"{PROMPT_INSTRUCTIVO}\n\n{resumen_usuario.strip()}\n\n{historial_context}"

# ==============================
# PROMPT PRINCIPAL ESTRUCTURADO
# ==============================

PROMPT_INSTRUCTIVO = """
#OBJETIVO PRINCIPAL
Eres BaekhoBot 🥋, el asistente comercial más especializado en productos de Taekwondo de Colombia. Tu objetivo principal es ayudar a cada cliente a encontrar el equipamiento perfecto según su nivel, presupuesto y necesidades específicas, usando información actualizada de la base de datos vectorial cuando esté disponible.

#CARACTERÍSTICAS DEL GPT
- Rol Profesional: Consultor comercial especialista en equipamiento de Taekwondo
- Priorizas información de la base vectorial (RAG) sobre conocimientos generales cuando esté disponible
- Mantienes conversaciones naturales y fluidas recordando el contexto anterior
- Adaptas la longitud de respuestas: cortas para consultas simples, detalladas solo cuando se solicite catálogo completo
- Nunca muestras elementos de formato markdown (###, **, ~~, etc.) al usuario final

#INSTRUCCIONES DEL GPT
1. **PRIORIZAR INFORMACIÓN RAG**: Si hay resultados de búsqueda vectorial, úsalos como fuente principal de verdad
2. **RESPUESTAS CONCISAS**: Máximo 3-4 oraciones por respuesta estándar (400 caracteres aprox.)
3. **MANTENER CONTEXTO**: Utiliza el historial y estado del usuario para personalizar respuestas
4. **CITAR FUENTES**: Cuando uses datos de RAG, menciona "según nuestro catálogo actualizado"
5. **GUIAR CONVERSACIÓN**: Termina siempre con una pregunta específica para mantener el flujo
6. **SIN FORMATO MARKDOWN**: Jamás incluyas ###, **, ~~, etc. en la respuesta final al usuario

#ESTILO DE COMUNICACIÓN
- Formato de respuesta: Conversacional, directo y amigable
- Estructura: Máximo 2 emojis por mensaje, información clave resaltada naturalmente
- Vocabulario: Técnico-comercial pero accesible para todos los niveles
- Tono: Amigable, profesional, consultivo y experto

#ESTRUCTURA DE LA RESPUESTA
##SALUDO (Solo primera interacción)
Bienvenida breve + identificación de necesidad básica

##INFORMACIÓN PRINCIPAL
- Datos específicos de RAG (cuando disponible) o conocimiento base
- Recomendación personalizada según estado del usuario
- Rango de precios relevante

##SIGUIENTE PASO
Pregunta específica para continuar la asesoría comercial

#EJEMPLOS
>>>>INICIO EJEMPLO 1
Usuario: "Hola, necesito un dobok"
BaekhoBot: "¡Hola! 🥋 Perfecto, te ayudo a encontrar el dobok ideal. Según nuestro catálogo actualizado, tenemos opciones desde 100.000 COP (principiante) hasta 1.000.000 COP (premium).

¿Cuál es tu nivel actual en Taekwondo?"
FIN EJEMPLO 1<<<<

>>>>INICIO EJEMPLO 2
Usuario: "Soy cinturón verde, busco algo para entrenamientos"
BaekhoBot: "Ideal para nivel intermedio. Te recomiendo nuestro dobok de competición (240.000-480.000 COP) con certificación WTF, perfecto para tu nivel y resistente para entrenamientos intensivos.

¿Cuál es tu presupuesto aproximado para el dobok?"
FIN EJEMPLO 2<<<<

>>>>INICIO EJEMPLO 3
Usuario: "¿Qué protecciones necesito para sparring?"
BaekhoBot: "Para sparring seguro necesitas el kit intermedio: peto + casco + espinilleras + antebrazos. Según nuestro inventario actualizado, el conjunto completo está entre 600.000-900.000 COP.

¿Es tu primera vez comprando protecciones o ya tienes algunas piezas?"
FIN EJEMPLO 3<<<<

#INDICACIONES SITUACIONALES
- **Con resultados RAG**: Prioriza completamente esos datos y menciona "según nuestro catálogo actualizado"
- **Sin resultados RAG**: Usa conocimiento general y especifica "información general de productos"
- **Conversación perdida**: Pregunta directamente qué información específica necesita
- **Presupuesto mencionado**: Enfócate únicamente en opciones dentro de ese rango
- **Usuario avanzado**: Ofrece opciones técnicas y de competición
- **Usuario principiante**: Enfócate en lo esencial y básico

#INSTRUCCIONES DE USO (DE CARA AL USUARIO)
Si el usuario solicita instrucciones de uso, responde con el siguiente mensaje:
__
💡 INSTRUCCIONES DE USO:
- Compárteme tu nivel de Taekwondo (principiante, intermedio, avanzado, competidor)
- Dime qué productos necesitas (dobok, protecciones, cinturón, accesorios)  
- Indica tu presupuesto aproximado si lo tienes en mente
- Pregúntame por promociones y packs especiales disponibles
__

#CARACTERÍSTICAS DEL USUARIO
- Rol Profesional: Practicantes de Taekwondo de todos los niveles (niños a adultos)
- Valores y Principios: Buscan calidad, precio justo, seguridad y asesoría experta
- Preferencias de Aprendizaje: Respuestas directas, opciones claras, comparaciones útiles

#PROMPTS NEGATIVOS
- Bajo ninguna circunstancia muestres elementos markdown (###, **, ~~, __) en respuestas finales
- No proporciones respuestas de más de 4 líneas a menos que sea un catálogo completo solicitado específicamente
- No hables de historia, técnicas, filosofía o entrenamiento del Taekwondo, SOLO productos comerciales
- No menciones competidores, otras tiendas o marcas no disponibles
- No inventes precios o especificaciones si no tienes datos RAG precisos

#HEURÍSTICOS
- El usuario busca soluciones específicas, no información general educativa
- Mantén siempre el foco comercial: producto → precio → recomendación → siguiente paso
- La brevedad y precisión generan más engagement que textos largos
- Siempre confirma presupuesto antes de recomendar productos costosos (+500.000 COP)
- Si el usuario parece perdido, simplifica y ofrece opciones básicas primero

#BASE DE CONOCIMIENTOS
- Recurre prioritariamente al contexto RAG proporcionado por búsquedas vectoriales
- Usa precios y especificaciones exactas de la base vectorial cuando estén disponibles
- Complementa con conocimiento general SOLO cuando no hay datos RAG
- Siempre especifica la fuente: "catálogo actualizado" (RAG) vs "información general" (base)

#CATEGORÍAS PRINCIPALES DE PRODUCTOS
🥋 **DOBOKS**: 100.000-1.000.000 COP (principiante, competición, premium)
🛡️ **PROTECCIONES**: 160.000-4.000.000 COP (básicas, intermedias, completas, electrónicas)
🏅 **CINTURONES**: 32.000-240.000 COP (todos los colores y materiales)
🥊 **ACCESORIOS**: 60.000-1.200.000 COP (paos, sacos, bolsas, equipos)

#PROMOCIONES ACTIVAS
- Pack Inicio: 336.000 COP (ahorra 144.000 COP)
- Pack Competidor: 1.200.000 COP (ahorra 400.000 COP)  
- Descuentos por volumen: 15-25% en compras grupales
- Financiamiento sin intereses hasta 3 meses
"""

# ==============================
# HERRAMIENTA DE BÚSQUEDA VECTORIAL
# ==============================

class TaekwondoVectorSearchTool(VectorSearchTool):
    """Herramienta especializada para búsqueda de productos de Taekwondo"""
    
    def __init__(self, agent: Agent):
        super().__init__(agent)
        self.description = "Busca productos específicos de Taekwondo en la base de datos vectorial"
    
    def search_products(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Ejecuta búsqueda vectorial y formatea resultados"""
        try:
            if not hasattr(self.agent, 'vecdb') or self.agent.vecdb is None:
                logger.warning("⚠️ Base vectorial no disponible")
                return []
            
            results = self.agent.vecdb.search(
                query=query,
                limit=limit,
                threshold=0.6  # Umbral de relevancia
            )
            
            formatted_results = []
            for result in results:
                if hasattr(result, 'payload') and result.payload:
                    formatted_results.append({
                        "nombre": result.payload.get("nombre", "N/A"),
                        "precio": result.payload.get("precio", "N/A"),
                        "categoria": result.payload.get("categoria", "N/A"),
                        "descripcion": result.payload.get("descripcion", "N/A")[:200],
                        "tallas": result.payload.get("tallas", "N/A"),
                        "material": result.payload.get("material", "N/A"),
                        "score": getattr(result, 'score', 0)
                    })
            
            logger.info(f"🔍 Búsqueda vectorial '{query}': {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda vectorial: {e}")
            return []
    
    def format_rag_context(self, results: List[Dict[str, Any]]) -> str:
        """Formatea resultados RAG para el prompt"""
        if not results:
            return ""
        
        context_parts = [
            "🔍 INFORMACIÓN DEL CATÁLOGO ACTUALIZADO:",
            ""
        ]
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"{i}. {result['nombre']}")
            context_parts.append(f"   💰 Precio: {result['precio']} COP")
            context_parts.append(f"   📂 Categoría: {result['categoria']}")
            context_parts.append(f"   📝 Descripción: {result['descripcion']}")
            if result.get('tallas') != 'N/A':
                context_parts.append(f"   📏 Tallas: {result['tallas']}")
            if result.get('material') != 'N/A':
                context_parts.append(f"   🧵 Material: {result['material']}")
            context_parts.append("")
        
        context_parts.append("⚠️ INSTRUCCIÓN: Usa PRIORITARIAMENTE esta información del catálogo.")
        context_parts.append("Menciona que proviene de 'nuestro catálogo actualizado'.")
        
        return "\n".join(context_parts)

# ==============================
# AGENTE PRINCIPAL LANGROID
# ==============================

class BaekhoLangroidAgent(Agent):
    """Agente principal BaekhoBot usando Langroid framework"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        
        # Estados conversacionales
        self.conversation_states: Dict[str, State] = {}
        
        # Herramientas
        self.vector_search_tool = TaekwondoVectorSearchTool(self)
        
        logger.info("✅ BaekhoLangroidAgent inicializado correctamente")
    
    def get_conversation_state(self, user_id: str) -> State:
        """Obtiene o crea el estado conversacional del usuario"""
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = State(user_id=user_id)
        return self.conversation_states[user_id]
    
    def analyze_message(self, message: str, state: State) -> Dict[str, Any]:
        """Analiza el mensaje y actualiza el estado del usuario"""
        message_lower = message.lower()
        
        analysis = {
            "intent": "general",
            "needs_vector_search": False,
            "search_query": "",
            "detected_entities": {}
        }
        
        # Detectar intenciones principales
        if any(word in message_lower for word in ["hola", "buenos", "buenas", "saludos", "hi"]):
            analysis["intent"] = "greeting"
            state.was_greeted = True
            state.phase = ConversationPhase.NEEDS_ASSESSMENT
            
        elif "dobok" in message_lower or "uniforme" in message_lower:
            analysis["intent"] = "dobok_inquiry"
            analysis["needs_vector_search"] = True
            analysis["search_query"] = f"dobok uniforme taekwondo {message_lower}"
            if "doboks" not in state.interested_categories:
                state.interested_categories.append("doboks")
            
        elif any(word in message_lower for word in ["proteccion", "casco", "peto", "espinillera", "guante"]):
            analysis["intent"] = "protection_inquiry"
            analysis["needs_vector_search"] = True
            analysis["search_query"] = f"protecciones seguridad taekwondo {message_lower}"
            if "protecciones" not in state.interested_categories:
                state.interested_categories.append("protecciones")
            
        elif "cinturon" in message_lower or "cinta" in message_lower:
            analysis["intent"] = "belt_inquiry"
            analysis["needs_vector_search"] = True
            analysis["search_query"] = f"cinturon cinta taekwondo {message_lower}"
            if "cinturones" not in state.interested_categories:
                state.interested_categories.append("cinturones")
                
        elif any(word in message_lower for word in ["precio", "cuesta", "vale", "barato", "caro", "costo"]):
            analysis["intent"] = "price_inquiry"
            state.phase = ConversationPhase.PRICE_DISCUSSION
            
        elif any(word in message_lower for word in ["talla", "medida", "tamaño", "size"]):
            analysis["intent"] = "size_inquiry"
            state.phase = ConversationPhase.SIZE_FITTING
            
        elif any(word in message_lower for word in ["promocion", "descuento", "oferta", "rebaja"]):
            analysis["intent"] = "promotion_inquiry"
            
        # Detectar nivel del usuario
        if any(word in message_lower for word in ["principiante", "comenzar", "empezar", "nuevo", "inicio"]):
            state.level = UserLevel.BEGINNER
            analysis["detected_entities"]["level"] = "principiante"
        elif any(word in message_lower for word in ["intermedio", "verde", "azul"]):
            state.level = UserLevel.INTERMEDIATE  
            analysis["detected_entities"]["level"] = "intermedio"
        elif any(word in message_lower for word in ["avanzado", "negro", "competir", "torneos"]):
            state.level = UserLevel.ADVANCED
            analysis["detected_entities"]["level"] = "avanzado"
        elif any(word in message_lower for word in ["instructor", "maestro", "profesor"]):
            state.level = UserLevel.INSTRUCTOR
            analysis["detected_entities"]["level"] = "instructor"
        
        # Detectar información de presupuesto
        if any(word in message_lower for word in ["barato", "economico", "poco dinero", "ajustado"]):
            state.budget_range = "Bajo (menos de 300.000 COP)"
            analysis["detected_entities"]["budget"] = "bajo"
        elif any(word in message_lower for word in ["premium", "mejor calidad", "no importa precio", "alto"]):
            state.budget_range = "Alto (más de 800.000 COP)"
            analysis["detected_entities"]["budget"] = "alto"
        elif any(word in message_lower for word in ["intermedio", "moderado", "medio"]):
            state.budget_range = "Medio (300.000-800.000 COP)"
            analysis["detected_entities"]["budget"] = "medio"
        
        return analysis
    
    async def process_message(self, message: str, user_info: Dict[str, Any] = None) -> str:
        """Procesa mensaje principal con RAG y estado conversacional"""
        try:
            # Obtener user_id
            user_id = user_info.get('user_id', 'unknown') if user_info else 'unknown'
            
            # Obtener estado conversacional
            state = self.get_conversation_state(user_id)
            state.context = f"Mensaje #{state.message_count + 1}"
            
            # Analizar mensaje
            analysis = self.analyze_message(message, state)
            
            # Realizar búsqueda vectorial si es necesaria
            vector_results = []
            rag_context = ""
            
            if analysis["needs_vector_search"]:
                search_query = analysis["search_query"] or message
                vector_results = self.vector_search_tool.search_products(search_query, limit=3)
                
                if vector_results:
                    rag_context = self.vector_search_tool.format_rag_context(vector_results)
                    logger.info(f"✅ RAG activado: {len(vector_results)} productos encontrados")
                else:
                    logger.info("⚠️ RAG sin resultados, usando conocimiento base")
            
            # Construir prompt completo
            base_prompt = build_prompt(state)
            
            # Añadir contexto RAG si está disponible
            if rag_context:
                full_prompt = f"{base_prompt}\n\n{rag_context}\n\n📝 CONSULTA ACTUAL: {message}"
            else:
                full_prompt = f"{base_prompt}\n\n⚠️ SIN DATOS RAG: Usar conocimiento general.\n\n📝 CONSULTA ACTUAL: {message}"
            
            # Generar respuesta
            response = await self.llm_response_async(full_prompt)
            
            # Limpiar respuesta
            clean_response = self.clean_response(response.content if hasattr(response, 'content') else str(response))
            
            # Actualizar estado
            state.history_messages.append(f"U: {message[:80]}... | B: {clean_response[:80]}...")
            if len(state.history_messages) > 5:
                state.history_messages.pop(0)
            
            state.message_count += 1
            state.last_activity = datetime.now()
            
            # Actualizar necesidades identificadas
            if analysis["intent"] not in ["greeting", "general"]:
                need = f"{analysis['intent']}_{datetime.now().strftime('%H:%M')}"
                if need not in state.identified_needs:
                    state.identified_needs.append(need)
            
            return clean_response
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje en BaekhoLangroidAgent: {e}")
            return self.get_fallback_response()
    
    def clean_response(self, response: str) -> str:
        """Limpia la respuesta eliminando elementos de formato no deseados"""
        # Remover markdown completamente
        response = response.replace("###", "")
        response = response.replace("##", "")
        response = response.replace("**", "")
        response = response.replace("~~", "")
        response = response.replace("__", "")
        response = response.replace("***", "")
        
        # Remover saltos de línea excesivos
        while "\n\n\n" in response:
            response = response.replace("\n\n\n", "\n\n")
        
        # Limitar longitud si es muy largo (más de 600 caracteres)
        if len(response) > 600:
            # Buscar el último punto antes del límite para cortar elegantemente
            cutoff_point = response[:550].rfind(".")
            if cutoff_point > 400:  # Solo cortar si hay un punto razonable
                response = response[:cutoff_point + 1]
                response += "\n\n¿Te ayudo con algo más específico? 🤔"
        
        return response.strip()
    
    def get_fallback_response(self) -> str:
        """Respuesta de emergencia cuando hay errores"""
        return """🥋 ¡Hola! Soy BaekhoBot, especialista en productos de Taekwondo.

Te ayudo a encontrar el equipamiento perfecto para tu práctica.

¿Qué necesitas hoy: dobok, protecciones o cinturón? 🎯"""
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtiene resumen del estado conversacional"""
        if user_id not in self.conversation_states:
            return {"error": "Conversación no encontrada"}
        
        state = self.conversation_states[user_id]
        return {
            "user_id": user_id,
            "phase": state.phase.value,
            "level": state.level.value if state.level else None,
            "budget_range": state.budget_range,
            "needs": state.identified_needs,
            "categories": state.interested_categories,
            "message_count": state.message_count,
            "was_greeted": state.was_greeted,
            "last_activity": state.last_activity.isoformat() if state.last_activity else None
        }

# ==============================
# AGENTE DE FALLBACK (Sin RAG)
# ==============================

class FallbackTaekwondoAgent:
    """Agente de respaldo sin Langroid para casos de emergencia"""
    
    def __init__(self):
        self.conversation_states: Dict[str, State] = {}
        logger.info("✅ FallbackTaekwondoAgent inicializado")
    
    def get_conversation_state(self, user_id: str) -> State:
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = State(user_id=user_id)
        return self.conversation_states[user_id]
    
    async def process_message(self, message: str, user_info: Dict[str, Any] = None) -> str:
        """Procesamiento simple sin RAG"""
        user_id = user_info.get('user_id', 'unknown') if user_info else 'unknown'
        state = self.get_conversation_state(user_id)
        
        # Detección simple de intención
        intent = self.detect_intent(message.lower())
        response = self.get_intent_response(intent, state)
        
        # Actualizar estado básico
        state.message_count += 1
        state.history_messages.append(f"U: {message[:50]}... | B: {response[:50]}...")
        if len(state.history_messages) > 3:
            state.history_messages.pop(0)
        
        return response
    
    def detect_intent(self, message: str) -> str:
        """Detección simple de intenciones"""
        if any(word in message for word in ["hola", "buenos", "saludos"]):
            return "greeting"
        elif "dobok" in message:
            return "dobok"
        elif any(word in message for word in ["proteccion", "casco", "peto"]):
            return "protection"
        elif "precio" in message:
            return "price"
        else:
            return "general"
    
    def get_intent_response(self, intent: str, state: State) -> str:
        """Respuestas hardcodeadas por intención"""
        responses = {
            "greeting": """🥋 ¡Hola! Soy BaekhoBot, especialista en productos de Taekwondo.

Te ayudo a encontrar el equipamiento perfecto según tu nivel.

¿Eres principiante, intermedio o avanzado?""",
            
            "dobok": """🥋 Doboks disponibles:
• Principiante: 100.000-180.000 COP
• Competición: 240.000-480.000 COP
• Premium: 400.000-1.000.000 COP

¿Cuál es tu nivel actual?""",
            
            "protection": """🛡️ Protecciones por nivel:
• Básicas: 160.000-320.000 COP
• Completas: 800.000-1.600.000 COP

¿Para qué tipo de entrenamiento?""",
            
            "price": """💰 Rangos generales:
• Principiante: 240.000-400.000 COP
• Intermedio: 600.000-1.000.000 COP
• Avanzado: 1.200.000+ COP

¿Cuál es tu presupuesto?""",
            
            "general": """🥋 ¿En qué te puedo ayudar?
• Doboks y uniformes
• Protecciones completas
• Cinturones
• Precios y tallas

¿Qué necesitas específicamente?"""
        }
        
        return responses.get(intent, responses["general"])

# ==============================
# FACTORY Y CONFIGURACIÓN PRINCIPAL
# ==============================

def create_baekho_agent() -> BaekhoLangroidAgent:
    """Factory para crear el agente BaekhoBot con Langroid"""
    try:
        # Configuraciones
        llm_config = get_llm_config()
        
        # Configuración del agente
        agent_config = ChatAgentConfig(
            name="BaekhoBot",
            system_message=PROMPT_INSTRUCTIVO,
            llm=llm_config,
            max_tokens=400,
            vecdb=None  # Se configurará después si Qdrant está disponible
        )
        
        # Crear agente
        agent = BaekhoLangroidAgent(agent_config)
        
        # Configurar base vectorial si está disponible
        try:
            qdrant_config = get_qdrant_config()
            embedding_config = get_embedding_config()
            
            # Crear conexión a Qdrant
            vecdb = QdrantDB(qdrant_config)
            agent.vecdb = vecdb
            
            logger.info("✅ Qdrant configurado correctamente para RAG")
            
        except Exception as e:
            logger.warning(f"⚠️ Qdrant no disponible, funcionando sin RAG: {e}")
            agent.vecdb = None
        
        return agent
        
    except Exception as e:
        logger.error(f"❌ Error creando agente Langroid: {e}")
        raise

def create_task_agent() -> Task:
    """Crea una tarea Langroid con el agente BaekhoBot"""
    try:
        agent = create_baekho_agent()
        task = Task(
            agent,
            name="BaekhoBot_Task",
            system_message="Asistente comercial especializado en productos de Taekwondo",
            llm_delegate=True,
            single_round=False
        )
        
        logger.info("✅ Task Langroid creada correctamente")
        return task
        
    except Exception as e:
        logger.error(f"❌ Error creando task Langroid: {e}")
        raise

# ==============================
# ORQUESTADOR PRINCIPAL (RAG + FALLBACK)
# ==============================

class EnhancedBaekhoAgent:
    """Orquestador principal que maneja RAG con Langroid y fallback"""
    
    def __init__(self):
        self.langroid_agent = None
        self.fallback_agent = FallbackTaekwondoAgent()
        self.rag_available = False
        
        # Intentar inicializar Langroid
        try:
            self.langroid_agent = create_baekho_agent()
            self.rag_available = hasattr(self.langroid_agent, 'vecdb') and self.langroid_agent.vecdb is not None
            logger.info(f"✅ EnhancedBaekhoAgent inicializado - RAG: {'✅' if self.rag_available else '❌'}")
        except Exception as e:
            logger.error(f"⚠️ Error inicializando Langroid, usando solo fallback: {e}")
    
    async def process_message(self, message: str, user_info: Dict[str, Any] = None) -> str:
        """Procesa mensaje con prioridad Langroid RAG y fallback"""
        try:
            # Intentar con Langroid primero
            if self.langroid_agent:
                try:
                    response = await self.langroid_agent.process_message(message, user_info)
                    
                    # Validar respuesta útil
                    if response and len(response.strip()) > 10 and not any(
                        error_indicator in response.lower() 
                        for error_indicator in ["error", "❌", "no disponible", "problema"]
                    ):
                        logger.debug("✅ Respuesta generada con Langroid RAG")
                        return response
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error con Langroid, usando fallback: {e}")
            
            # Fallback al agente simple
            logger.info("💡 Usando agente de fallback")
            return await self.fallback_agent.process_message(message, user_info)
            
        except Exception as e:
            logger.error(f"❌ Error en orquestador principal: {e}")
            return self.get_emergency_response()
    
    def get_emergency_response(self) -> str:
        """Respuesta de emergencia absoluta"""
        return """🥋 ¡Hola! Soy BaekhoBot, tu especialista en productos de Taekwondo.

Tengo una pequeña falla técnica, pero puedo ayudarte con lo básico:
• Doboks: 100.000-1.000.000 COP
• Protecciones: 160.000-4.000.000 COP
• Cinturones: 32.000-240.000 COP

¿Qué necesitas hoy? 🎯"""
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtiene resumen conversacional desde el agente activo"""
        try:
            if self.langroid_agent:
                return self.langroid_agent.get_conversation_summary(user_id)
            else:
                # Resumen básico del fallback
                state = self.fallback_agent.get_conversation_state(user_id)
                return {
                    "user_id": user_id,
                    "message_count": state.message_count,
                    "agent_type": "fallback",
                    "rag_available": False
                }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {"error": "No se pudo obtener resumen"}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Información del modelo y capacidades"""
        return {
            "langroid_available": self.langroid_agent is not None,
            "rag_available": self.rag_available,
            "fallback_available": True,
            "capabilities": {
                "vector_search": self.rag_available,
                "conversation_state": True,
                "product_catalog": True,
                "price_recommendations": True,
                "smart_responses": True
            },
            "model_info": {
                "primary": "gpt-4o-mini (Langroid)" if self.langroid_agent else "Fallback",
                "embedding": "text-embedding-ada-002" if self.rag_available else "N/A",
                "vector_db": "Qdrant" if self.rag_available else "N/A"
            }
        }
    
    async def reset_conversation(self, user_id: str) -> bool:
        """Reinicia la conversación de un usuario"""
        try:
            if self.langroid_agent and user_id in self.langroid_agent.conversation_states:
                del self.langroid_agent.conversation_states[user_id]
            
            if user_id in self.fallback_agent.conversation_states:
                del self.fallback_agent.conversation_states[user_id]
            
            logger.info(f"🔄 Conversación reiniciada para usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reiniciando conversación: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del sistema"""
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Verificar Langroid
        try:
            if self.langroid_agent:
                health["components"]["langroid"] = "✅ Available"
                
                # Verificar RAG
                if self.rag_available:
                    health["components"]["rag"] = "✅ Available"
                else:
                    health["components"]["rag"] = "⚠️ Not available"
            else:
                health["components"]["langroid"] = "❌ Not available"
                health["status"] = "degraded"
                
        except Exception as e:
            health["components"]["langroid"] = f"❌ Error: {str(e)}"
            health["status"] = "degraded"
        
        # Verificar Fallback
        try:
            health["components"]["fallback"] = "✅ Available"
        except Exception as e:
            health["components"]["fallback"] = f"❌ Error: {str(e)}"
            health["status"] = "critical"
        
        return health

# ==============================
# FUNCIONES DE UTILIDAD
# ==============================

async def test_agent() -> None:
    """Función de prueba para verificar el agente"""
    try:
        agent = EnhancedBaekhoAgent()
        
        # Prueba básica
        test_messages = [
            "Hola, necesito un dobok",
            "Soy cinturón verde",
            "¿Cuánto cuesta?",
            "Necesito protecciones también"
        ]
        
        user_info = {"user_id": "test_user_123"}
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{'='*50}")
            print(f"PRUEBA {i}: {message}")
            print(f"{'='*50}")
            
            response = await agent.process_message(message, user_info)
            print(f"RESPUESTA: {response}")
            
            # Pausa entre mensajes
            await asyncio.sleep(0.5)
        
        # Mostrar resumen
        summary = agent.get_conversation_summary("test_user_123")
        print(f"\n{'='*50}")
        print("RESUMEN CONVERSACIONAL:")
        print(f"{'='*50}")
        for key, value in summary.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

def get_agent_instance() -> EnhancedBaekhoAgent:
    """Obtiene una instancia singleton del agente"""
    if not hasattr(get_agent_instance, "_instance"):
        get_agent_instance._instance = EnhancedBaekhoAgent()
    return get_agent_instance._instance

# ==============================
# EXPORTACIONES
# ==============================

# Exportar las clases principales para uso en otros módulos
__all__ = [
    "EnhancedBaekhoAgent",
    "BaekhoLangroidAgent", 
    "FallbackTaekwondoAgent",
    "State",
    "ConversationPhase",
    "UserLevel",
    "create_baekho_agent",
    "create_task_agent",
    "get_agent_instance",
    "test_agent"
]

# Instancia global para importación directa
TaekwondoAgent = EnhancedBaekhoAgent  # Alias para compatibilidad
BaekhoAgent = EnhancedBaekhoAgent     # Nombre principal

if __name__ == "__main__":
    # Ejecutar prueba si se ejecuta directamente
    asyncio.run(test_agent())