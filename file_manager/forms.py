from django import forms
from .models import File, FileCategory, Tag, FileComment, FileVersion

class FileUploadForm(forms.ModelForm):
    """Форма загрузки файла"""
    class Meta:
        model = File
        fields = ['title', 'description', 'file', 'category', 'tags', 'visibility', 'shared_with', 'folder']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'shared_with': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'folder': forms.Select(attrs={'class': 'form-select'}),
        }

class FileEditForm(forms.ModelForm):
    """Форма редактирования файла (без загрузки нового файла)"""
    class Meta:
        model = File
        fields = ['title', 'description', 'category', 'tags', 'visibility', 'shared_with']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'shared_with': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }

class FileVersionForm(forms.ModelForm):
    """Форма для новой версии файла"""
    class Meta:
        model = FileVersion
        fields = ['version_file', 'change_description']
        widgets = {
            'version_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'change_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FileCommentForm(forms.ModelForm):
    """Форма комментария к файлу"""
    class Meta:
        model = FileComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class FileCategoryForm(forms.ModelForm):
    """Форма категории файлов"""
    class Meta:
        model = FileCategory
        fields = ['name', 'description', 'icon', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class TagForm(forms.ModelForm):
    """Форма тега"""
    class Meta:
        model = Tag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }

class FileSearchForm(forms.Form):
    """Форма поиска файлов"""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    file_type = forms.ChoiceField(
        choices=[('', 'Все типы')] + File.FILE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=FileCategory.objects.all(),
        required=False,
        empty_label='Все категории',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )