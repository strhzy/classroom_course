import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        from .models import ChatRoom

        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)

            if room.participants.filter(id=self.scope['user'].id).exists():
                async_to_sync(self.channel_layer.group_add)(
                    self.room_group_name,
                    self.channel_name
                )
                self.accept()
            else:
                self.close()
        except ChatRoom.DoesNotExist:
            self.close()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        from .models import ChatRoom, Message
        from django.contrib.auth.models import User

        user = User.objects.get(id=self.scope['user'].id)
        room = ChatRoom.objects.get(id=self.room_id)

        msg = Message.objects.create(
            room=room,
            user=user,
            content=message
        )

        # 🔥 ВАЖНО: async_to_sync
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': user.id,
                'username': user.username,
                'timestamp': msg.timestamp.isoformat()
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))