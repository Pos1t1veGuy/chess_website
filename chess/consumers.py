import json
from channels.generic.websocket import WebsocketConsumer

class searchConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
    
    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        
        # Логика обработки сообщения
        
        self.send(text_data=json.dumps({
            'message': '...'
        }))
