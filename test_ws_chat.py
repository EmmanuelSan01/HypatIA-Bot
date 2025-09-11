import asyncio
import websockets

async def test_ws_chat():
    uri = "ws://localhost:8000/ws/chat"
    print(f"Conectando a {uri} ...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conexión WebSocket establecida")
            mensaje = "Hola, chatbot! ¿Qué cursos tienes?"
            print(f"→ Enviando: {mensaje}")
            await websocket.send(mensaje)
            respuesta = await websocket.recv()
            print(f"← Respuesta del chatbot: {respuesta}")
    except Exception as e:
        print(f"❌ Error en la conexión WebSocket: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws_chat())
