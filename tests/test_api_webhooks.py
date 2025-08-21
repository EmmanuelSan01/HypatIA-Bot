import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from main import app

# Crear cliente de prueba
client = TestClient(app)

class TestAPIEndpoints:
    """Pruebas unitarias y de integración para los endpoints de la API"""
    
    def test_health_endpoint(self):
        """Prueba el endpoint GET /health"""
        # Realizar solicitud GET al endpoint de salud
        response = client.get("/health")
        
        # Verificar código de estado
        assert response.status_code == 200
        
        # Verificar estructura de respuesta
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    @patch('app.controllers.telegram.TelegramController.process_message')
    @patch('app.controllers.telegram.TelegramController._send_telegram_message')
    def test_telegram_webhook_endpoint(self, mock_send_message, mock_process_message):
        """Prueba el endpoint POST /telegram/webhook"""
        # Configurar mocks
        mock_send_message.return_value = True
        mock_process_message.return_value = None
        
        # Simular mensaje de Telegram
        telegram_message = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 987654321,
                    "first_name": "Usuario",
                    "username": "test_user"
                },
                "chat": {
                    "id": 987654321,
                    "type": "private"
                },
                "date": 1640995200,
                "text": "Hola bot"
            }
        }
        
        # Realizar solicitud POST al webhook de Telegram
        response = client.post("/telegram/webhook", json=telegram_message)
        
        # Verificar código de estado
        assert response.status_code == 200
        
        # Verificar que la respuesta es JSON válido
        try:
            data = response.json()
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("La respuesta no es JSON válido")
    
    def test_root_endpoint(self):
        """Prueba el endpoint GET / (endpoint raíz)"""
        # Realizar solicitud GET al endpoint raíz
        response = client.get("/")
        
        # Verificar código de estado
        assert response.status_code == 200
        
        # Verificar estructura de respuesta
        data = response.json()
        assert "message" in data
        assert "status" in data
    
    def test_telegram_webhook_invalid_payload(self):
        """Prueba el endpoint POST /telegram/webhook con payload inválido"""
        # Payload inválido de Telegram
        invalid_payload = {
            "invalid": "data"
        }
        
        # Realizar solicitud POST al webhook de Telegram
        response = client.post("/telegram/webhook", json=invalid_payload)
        
        # Verificar que maneja el payload inválido correctamente
        # Puede retornar 200 (acepta el webhook) o 400 (rechaza payload inválido)
        assert response.status_code in [200, 400]
    
    def test_telegram_webhook_missing_text(self):
        """Prueba el endpoint POST /telegram/webhook sin texto en el mensaje"""
        # Mensaje de Telegram sin texto
        telegram_message_no_text = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 987654321,
                    "first_name": "Usuario"
                },
                "chat": {
                    "id": 987654321,
                    "type": "private"
                },
                "date": 1640995200
                # Sin campo "text"
            }
        }
        
        # Realizar solicitud POST al webhook de Telegram
        response = client.post("/telegram/webhook", json=telegram_message_no_text)
        
        # Verificar que maneja mensajes sin texto correctamente
        assert response.status_code in [200, 400]
