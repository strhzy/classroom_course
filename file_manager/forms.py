from django import forms
from .models import File, FileVersion, FileComment
from classroom_core.models import Course

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'description', 'file', 'course', 'visibility', 'shared_with', 'folder']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название файла'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Описание файла', 'rows': 3}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'shared_with': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'folder': forms.Select(attrs={'class': 'form-select'}),
        }

class FileEditForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'description', 'course', 'visibility', 'shared_with']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'shared_with': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }

class FileVersionForm(forms.ModelForm):
    class Meta:
        model = FileVersion
        fields = ['version_file', 'change_description']
        widgets = {
            'version_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'change_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Описание изменений', 'rows': 3}),
        }

class FileCommentForm(forms.ModelForm):
    class Meta:
        model = FileComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Напишите комментарий...', 'rows': 3}),
        }

# Формы категорий и тегов удалены — управление через курсы

class FileSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по названию, описанию или содержимому...'})
    )
    file_type = forms.ChoiceField(
        choices=[('', 'Все типы')] + File.FILE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label='Все курсы',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    favorites_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )