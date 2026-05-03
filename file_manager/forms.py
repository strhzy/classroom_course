from django import forms 
from . models import File ,Tag ,FileComment ,FileVersion 

class FileEditForm(forms.ModelForm ):
    """Форма редактирования файла(без загрузки нового файла)"""
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

class FileVersionForm(forms.ModelForm ):
    """Форма для новой версии файла"""
    class Meta :
        model =FileVersion 
        fields =['version_file','change_description']
        widgets ={
        'version_file':forms.ClearableFileInput(attrs ={'class':'form-control'}),
        'change_description':forms.Textarea(attrs ={'class':'form-control','rows':3 }),
        }

class FileCommentForm(forms.ModelForm ):
    """Форма комментария к файлу"""
    class Meta :
        model =FileComment 
        fields =['content']
        widgets ={
        'content':forms.Textarea(attrs ={'class':'form-control','rows':3 }),
        }

class TagForm(forms.ModelForm ):
    """Форма тега"""
    class Meta :
        model =Tag 
        fields =['name','color']
        widgets ={
        'name':forms.TextInput(attrs ={'class':'form-control'}),
        'color':forms.TextInput(attrs ={'class':'form-control','type':'color'}),
        }

class FileSearchForm(forms.Form ):
    """Форма поиска файлов"""
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