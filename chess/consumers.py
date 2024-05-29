import json
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer

class searchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope['user'].is_authenticated:
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        
        # Логика обработки сообщения
        
        await self.send(text_data=json.dumps({
            'message': '123...123'
        }))
