from django import forms 
from django .contrib .auth .models import User 
from .models import *



class CourseSectionForm (forms .ModelForm ):
    """Форма для создания/редактирования раздела курса"""
    class Meta :
        model =CourseSection 
        fields =['title','description','order','is_visible']
        widgets ={
        'title':forms .TextInput (attrs ={'class':'form-control'}),
        'description':forms .Textarea (attrs ={'class':'form-control','rows':2 }),
        'order':forms .NumberInput (attrs ={'class':'form-control'}),
        'is_visible':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        }

class CourseMaterialForm (forms .ModelForm ):
    """Форма для создания/редактирования учебного материала"""
    class Meta :
        model =CourseMaterial 
        fields =[
        'title','description','material_type',
        'file','url','content','order','is_visible','is_required'
        ]
        widgets ={
        'title':forms .TextInput (attrs ={'class':'form-control'}),
        'description':forms .Textarea (attrs ={'class':'form-control','rows':2 }),
        'material_type':forms .Select (attrs ={'class':'form-select'}),
        'file':forms .ClearableFileInput (attrs ={'class':'form-control'}),
        'url':forms .URLInput (attrs ={'class':'form-control'}),
        'content':forms .Textarea (attrs ={'class':'form-control','rows':4 }),
        'order':forms .NumberInput (attrs ={'class':'form-control'}),
        'is_visible':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        'is_required':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        }

class AssignmentForm (forms .ModelForm ):
    """Форма для создания/редактирования задания"""
    class Meta :
        model =Assignment 
        fields =[
        'title',
        'description',
        'due_date',
        'max_points',
        'passing_score',
        'is_group_assignment',
        'group_size_min',
        'group_size_max',
        'attachment',
        'status'
        ]
        widgets ={
        'title':forms .TextInput (attrs ={'class':'form-control'}),
        'description':forms .Textarea (attrs ={'class':'form-control','rows':4 }),
        'due_date':forms .DateTimeInput (attrs ={'class':'form-control','type':'datetime-local'}),
        'max_points':forms .NumberInput (attrs ={'class':'form-control'}),
        'passing_score':forms .NumberInput (attrs ={'class':'form-control'}),
        'group_size_min':forms .NumberInput (attrs ={'class':'form-control'}),
        'group_size_max':forms .NumberInput (attrs ={'class':'form-control'}),
        'attachment':forms .ClearableFileInput (attrs ={'class':'form-control'}),
        'status':forms .Select (attrs ={'class':'form-select'}),
        'is_group_assignment':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        }

class AssignmentSubmissionForm (forms .ModelForm ):
    """Форма для отправки решения задания"""
    class Meta :
        model =AssignmentSubmission 
        fields =['text_response','file_submission']
        widgets ={
        'text_response':forms .Textarea (attrs ={'class':'form-control','rows':4 }),
        'file_submission':forms .ClearableFileInput (attrs ={'class':'form-control'}),
        }

class AssignmentGradeForm (forms .ModelForm ):
    """Форма для оценки задания"""
    class Meta :
        model =AssignmentSubmission 
        fields =['score','feedback','status']
        widgets ={
        'score':forms .NumberInput (attrs ={'class':'form-control'}),
        'feedback':forms .Textarea (attrs ={'class':'form-control','rows':4 }),
        'status':forms .Select (attrs ={'class':'form-select'}),
        }

class AnnouncementForm (forms .ModelForm ):
    """Форма для создания объявления"""
    class Meta :
        model =Announcement 
        fields =['title','content','is_pinned','send_email_notification']
        widgets ={
        'title':forms .TextInput (attrs ={'class':'form-control'}),
        'content':forms .Textarea (attrs ={'class':'form-control','rows':6 }),
        'is_pinned':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        'send_email_notification':forms .CheckboxInput (attrs ={'class':'form-check-input'}),
        }

class CourseForm(forms.ModelForm):
    """Форма для создания/редактирования курса"""
    class Meta:
        model = Course
        fields = [
            'title', 
            'description', 
            'short_description', 
            'start_date', 
            'end_date',
            'is_public',
            'allow_self_enrollment',
            'max_students',
            'cover_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_self_enrollment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class StudentEnrollmentForm(forms.Form):
    """Форма для зачисления студентов на курс"""
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(profile__role='student'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Индивидуальные студенты'
    )

class StudentGroupEnrollmentForm(forms.Form):
    """Форма для зачисления групп студентов на курс"""
    groups = forms.ModelMultipleChoiceField(
        queryset=StudentGroup.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Группы студентов'
    )

class StudentGroupForm(forms.ModelForm):
    """Форма для создания/редактирования группы студентов"""
    class Meta:
        model = StudentGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class UserProfileForm(forms.ModelForm):
    """Форма для редактирования профиля пользователя"""
    class Meta:
        model = UserProfile
        fields = ['role', 'department', 'position', 'student_group', 'phone', 'avatar']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'student_group': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }