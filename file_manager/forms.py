from django import forms 
from django.contrib.auth.models import User
from . models import File ,Tag ,FileComment 

class FileEditForm(forms.ModelForm ):
    class Meta :
        model =File 
        fields =['title','description','visibility','shared_with','tags']
        widgets ={
        'title':forms.TextInput(attrs ={'class':'form-control'}),
        'description':forms.Textarea(attrs ={'class':'form-control','rows':3 }),
        'visibility':forms.Select(attrs ={'class':'form-select'}),
        'shared_with':forms.SelectMultiple(attrs ={'class':'form-select','size':5 }),
        'tags': forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input flex-shrink-0'}
        ),
        }

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get("visibility")
        if visibility != "shared":
            cleaned_data["shared_with"] = []
        return cleaned_data

class FileVersionForm(forms.Form):
    version_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label='Новый файл',
    )
    change_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Описание изменений',
    )

    EXT_GROUPS = {
        "docx": {"doc", "docx"},
        "xlsx": {"xls", "xlsx"},
        "pptx": {"ppt", "pptx"},
        "jpg": {"jpg", "jpeg"},
        "txt": {"txt"},
        "pdf": {"pdf"},
        "png": {"png"},
        "mp4": {"mp4"},
        "mp3": {"mp3"},
        "zip": {"zip", "rar", "7z"},
    }

    def __init__(self, *args, **kwargs):
        self.current_file = kwargs.pop("current_file", None)
        super().__init__(*args, **kwargs)

    def _extract_ext(self, filename):
        value = (filename or "").strip().lower()
        if "." not in value:
            return ""
        return value.rsplit(".", 1)[-1]

    def _normalize_group(self, ext):
        ext = (ext or "").lower()
        for group, values in self.EXT_GROUPS.items():
            if ext in values:
                return group
        return ext or "unknown"

    def clean_version_file(self):
        uploaded = self.cleaned_data.get("version_file")
        if not uploaded or not self.current_file:
            return uploaded

        new_ext = self._extract_ext(uploaded.name)
        current_ext = (self.current_file.get_extension() or "").lower()
        if not new_ext or not current_ext:
            return uploaded

        if self._normalize_group(new_ext) != self._normalize_group(current_ext):
            raise forms.ValidationError(
                f"Нельзя сменить тип файла в версии: текущий .{current_ext}, загружен .{new_ext}."
            )
        return uploaded


class BulkPermissionForm(forms.Form):
    files = forms.ModelMultipleChoiceField(
        queryset=File.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Файлы',
    )
    visibility = forms.ChoiceField(
        choices=File.VISIBILITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Режим доступа',
    )
    shared_with = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Пользователи для общего доступа',
    )

    def __init__(self, *args, **kwargs):
        editable_files_qs = kwargs.pop("editable_files_qs", File.objects.none())
        share_users_qs = kwargs.pop("share_users_qs", User.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["files"].queryset = editable_files_qs
        self.fields["shared_with"].queryset = share_users_qs

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get("visibility")
        if visibility != "shared":
            cleaned_data["shared_with"] = []
        return cleaned_data

class FileCommentForm(forms.ModelForm ):
    class Meta :
        model =FileComment 
        fields =['content']
        widgets ={
        'content':forms.Textarea(attrs ={'class':'form-control','rows':3 }),
        }

class TagForm(forms.ModelForm ):
    class Meta :
        model =Tag 
        fields =['name','color']
        widgets ={
        'name':forms.TextInput(attrs ={'class':'form-control'}),
        'color':forms.TextInput(attrs ={'class':'form-control','type':'color'}),
        }

class FileSearchForm(forms.Form ):
    query =forms.CharField(
    required =False ,
    widget =forms.TextInput(attrs ={'class':'form-control'})
    )
    file_type =forms.ChoiceField(
    choices =[('','Все типы')]+File.FILE_TYPE_CHOICES ,
    required =False ,
    widget =forms.Select(attrs ={'class':'form-select'})
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input flex-shrink-0'}
        ),
    )
    favorites_only = forms.BooleanField(required=False)
    date_from =forms.DateField(
    required =False ,
    widget =forms.DateInput(attrs ={'class':'form-control','type':'date'})
    )
    date_to =forms.DateField(
    required =False ,
    widget =forms.DateInput(attrs ={'class':'form-control','type':'date'})
    )