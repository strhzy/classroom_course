import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.utils import timezone


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
        from .models import ChatRoom, Message
        from django.contrib.auth.models import User

        user = User.objects.get(id=self.scope['user'].id)
        room = ChatRoom.objects.get(id=self.room_id)

        if not room.participants.filter(id=user.id).exists():
            return

        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')

        if action == 'delete':
            self._handle_delete(room, user, text_data_json)
            return
        if action == 'edit':
            self._handle_edit(room, user, text_data_json)
            return

        message = text_data_json.get('message', '')
        file_url = text_data_json.get('file_url')
        file_name = text_data_json.get('file_name')
        is_image = text_data_json.get('is_image', False)
        file_size = text_data_json.get('file_size', '')
        file_extension = text_data_json.get('file_extension', '')

        if file_url and file_name:
            message_id = text_data_json.get('message_id')
            if not message_id:
                return
            try:
                msg = Message.objects.get(id=message_id, room=room, user=user)
            except Message.DoesNotExist:
                return
            if msg.is_deleted or not msg.file_attachment:
                return
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'file_message',
                    'message_id': msg.id,
                    'message': message or '',
                    'user_id': user.id,
                    'username': user.username,
                    'file_url': file_url,
                    'file_name': file_name,
                    'is_image': is_image,
                    'file_size': file_size,
                    'file_extension': file_extension,
                    'timestamp': msg.timestamp.isoformat(),
                }
            )
            return

        text = (message or '').strip()
        if not text:
            return

        msg = Message.objects.create(
            room=room,
            user=user,
            content=text
        )

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': msg.id,
                'message': text,
                'user_id': user.id,
                'username': user.username,
                'timestamp': msg.timestamp.isoformat(),
                'edited_at': None,
            }
        )

    def _handle_delete(self, room, user, data):
        from .models import Message

        message_id = data.get('message_id')
        if not message_id:
            return
        try:
            msg = Message.objects.get(id=message_id, room=room)
        except Message.DoesNotExist:
            return
        if msg.user_id != user.id or msg.is_deleted:
            return
        msg.is_deleted = True
        msg.content = ''
        msg.save(update_fields=['is_deleted', 'content'])

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'message_deleted',
                'message_id': msg.id,
            }
        )

    def _handle_edit(self, room, user, data):
        from .models import Message

        message_id = data.get('message_id')
        if not message_id:
            return
        raw = data.get('message')
        if raw is not None and not isinstance(raw, str):
            return
        raw = '' if raw is None else raw
        if len(raw) > 8000:
            return
        try:
            msg = Message.objects.get(id=message_id, room=room)
        except Message.DoesNotExist:
            return
        if msg.user_id != user.id or msg.is_deleted:
            return

        if msg.file_attachment:
            msg.content = raw
        else:
            stripped = raw.strip()
            if not stripped:
                return
            msg.content = stripped

        msg.edited_at = timezone.now()
        msg.save(update_fields=['content', 'edited_at'])

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'message_edited',
                'message_id': msg.id,
                'message': msg.content,
                'edited_at': msg.edited_at.isoformat(),
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'edited_at': event.get('edited_at'),
        }))

    def file_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'file_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'user_id': event['user_id'],
            'username': event['username'],
            'file_url': event['file_url'],
            'file_name': event['file_name'],
            'is_image': event['is_image'],
            'file_size': event['file_size'],
            'file_extension': event['file_extension'],
            'timestamp': event['timestamp'],
        }))

    def message_deleted(self, event):
        self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        }))

    def message_edited(self, event):
        self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'message': event['message'],
            'edited_at': event['edited_at'],
        }))
