from django import forms
from .models import Message

class ChatMessageForm(forms.ModelForm):
    """Форма для отправки сообщений в чате"""
    class Meta:
        model = Message
        fields = ['content', 'file_attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Введите сообщение...',
                'rows': 1,
                'class': 'chat-message-input'
            }),
        }
        labels = {
            'content': '',
            'file_attachment': ''
        }

class ChatFileUploadForm(forms.Form):
    """Форма для загрузки файлов в чат"""
    content = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Добавьте комментарий к файлу (необязательно)',
            'class': 'file-comment-input'
        })
    )
    file_attachment = forms.FileField(
        label='Выберите файл',
        help_text='Максимальный размер файла: 10 МБ'
    )
