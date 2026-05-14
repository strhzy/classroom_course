from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from . models import *
from file_manager.models import File


CLASS_WEEKDAY_ORDER = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
CLASS_WEEKDAY_CHOICES = (
    ("пн", "Пн"),
    ("вт", "Вт"),
    ("ср", "Ср"),
    ("чт", "Чт"),
    ("пт", "Пт"),
    ("сб", "Сб"),
    ("вс", "Вс"),
)


_WEEKDAY_ALIASES = {
    "mon": "пн", "monday": "пн",
    "tue": "вт", "tuesday": "вт",
    "wed": "ср", "wednesday": "ср",
    "thu": "чт", "thursday": "чт",
    "fri": "пт", "friday": "пт",
    "sat": "сб", "saturday": "сб",
    "sun": "вс", "sunday": "вс",
}


def _tokens_from_class_days_string(raw):
    """Разбор сохранённой строки class_days в упорядоченный список кодов дней (пн…вс)."""
    if not raw or not str(raw).strip():
        return []
    allowed = set(CLASS_WEEKDAY_ORDER)
    seen = []
    for token in str(raw).replace(" ", "").lower().split(","):
        if not token:
            continue
        t = _WEEKDAY_ALIASES.get(token, token)
        if t in allowed and t not in seen:
            seen.append(t)
    return sorted(seen, key=lambda x: CLASS_WEEKDAY_ORDER.index(x))


def _class_days_string_from_tokens(tokens):
    if not tokens:
        return ""
    uniq = []
    for t in tokens:
        if t in CLASS_WEEKDAY_ORDER and t not in uniq:
            uniq.append(t)
    uniq.sort(key=lambda t: CLASS_WEEKDAY_ORDER.index(t))
    return ",".join(uniq)


class CourseSectionForm(forms.ModelForm ):
    """Форма для создания/редактирования раздела курса"""
    class Meta :
        model =CourseSection 
        fields =['title','description','order','is_visible']
        widgets ={
        'title':forms.TextInput(attrs ={'class':'form-control'}),
        'description':forms.Textarea(attrs ={'class':'form-control','rows':2 }),
        'order':forms.NumberInput(attrs ={'class':'form-control'}),
        'is_visible':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        }

class CourseMaterialForm(forms.ModelForm ):
    """Форма для создания/редактирования учебного материала"""
    class Meta :
        model =CourseMaterial 
        fields =[
        'title','description','material_type',
        'file','url','content','order','is_visible','is_required','status'
        ]
        widgets ={
        'title':forms.TextInput(attrs ={'class':'form-control'}),
        'description':forms.Textarea(attrs ={'class':'form-control','rows':2 }),
        'material_type':forms.Select(attrs ={'class':'form-select'}),
        'file':forms.ClearableFileInput(attrs ={'class':'form-control'}),
        'url':forms.URLInput(attrs ={'class':'form-control'}),
        'content':forms.Textarea(attrs ={'class':'form-control','rows':4 }),
        'order':forms.NumberInput(attrs ={'class':'form-control'}),
        'is_visible':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        'is_required':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        'status': forms.Select(attrs={'class': 'form-select'}),
        }

class AssignmentForm(forms.ModelForm ):
    """Форма для создания/редактирования задания"""
    class Meta :
        model =Assignment 
        fields =[
        'title',
        'description',
        'due_date',
        'assignment_type',
        'quiz_mode',
        'max_points',
        'passing_score',
        'is_group_assignment',
        'attachment',
        'status'
        ]
        widgets ={
        'title':forms.TextInput(attrs ={'class':'form-control'}),
        'description':forms.Textarea(attrs ={'class':'form-control','rows':4 }),
        'due_date':forms.DateTimeInput(attrs ={'class':'form-control','type':'datetime-local'}),
        'assignment_type': forms.Select(attrs={'class': 'form-select'}),
        'quiz_mode': forms.Select(attrs={'class': 'form-select'}),
        'max_points':forms.NumberInput(attrs ={'class':'form-control'}),
        'passing_score':forms.NumberInput(attrs ={'class':'form-control'}),
        'attachment':forms.ClearableFileInput(attrs ={'class':'form-control'}),
        'status':forms.Select(attrs ={'class':'form-select'}),
        'is_group_assignment':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        assignment_type = cleaned_data.get("assignment_type")
        if assignment_type == "quiz":
            cleaned_data["is_group_assignment"] = False
        return cleaned_data

class AssignmentSubmitCombinedForm(forms.Form):
    """Единая отправка решения: текст + файл с устройства или из хранилища (→ AssignmentFile)."""

    text_response = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'custom-textarea',
            'rows': 6,
            'placeholder': 'Опишите ваше решение, добавьте пояснения или комментарии…',
            'id': 'id_text_response',
        }),
        label='Текстовое описание решения',
    )
    upload_from_pc = forms.FileField(
        required=False,
        label='Загрузить файл с устройства',
        widget=forms.FileInput(attrs={
            'class': 'file-input',
            'id': 'id_upload_from_pc',
            'onchange': 'updateFileName(this)',
        }),
        help_text='Сохраняется в вашем хранилище, как при обычной загрузке в файловом менеджере.',
    )
    storage_file = forms.ModelChoiceField(
        queryset=File.objects.none(),
        required=False,
        empty_label='— выберите уже загруженный файл —',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_storage_file'}),
        label='Или выберите файл из хранилища',
        help_text='Ваши файлы и файлы с общим доступом.',
    )
    attachment_description = forms.CharField(
        required=False,
        label='Описание к прикрепляемому файлу',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Если прикрепляете файл — краткий комментарий (необязательно)',
        }),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['storage_file'].queryset = File.objects.filter(
                Q(uploaded_by=user) | Q(visibility='public') | Q(shared_with=user),
            ).distinct().order_by('-uploaded_at')

    def clean(self):
        cleaned_data = super().clean()
        text = (cleaned_data.get('text_response') or '').strip()
        upload = cleaned_data.get('upload_from_pc')
        storage = cleaned_data.get('storage_file')
        if upload and storage:
            raise ValidationError(
                'Выберите один способ прикрепления файла: загрузка с устройства или файл из списка.'
            )
        if not text and not upload and not storage:
            raise ValidationError(
                'Укажите текст решения и/или прикрепите файл (с устройства или из хранилища).'
            )
        return cleaned_data


class AssignmentGradeForm(forms.ModelForm ):
    """Форма для оценки задания"""
    class Meta :
        model =AssignmentSubmission 
        fields =['score','feedback','status']
        widgets ={
        'score':forms.NumberInput(attrs ={'class':'form-control'}),
        'feedback':forms.Textarea(attrs ={'class':'form-control','rows':4 }),
        'status':forms.Select(attrs ={'class':'form-select'}),
        }

class AnnouncementForm(forms.ModelForm ):
    """Форма для создания объявления"""
    class Meta :
        model =Announcement 
        fields =['title','content','is_pinned','send_email_notification']
        widgets ={
        'title':forms.TextInput(attrs ={'class':'form-control'}),
        'content':forms.Textarea(attrs ={'class':'form-control','rows':6 }),
        'is_pinned':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        'send_email_notification':forms.CheckboxInput(attrs ={'class':'form-check-input'}),
        }

class CourseForm(forms.ModelForm):
    """Форма для создания/редактирования курса"""
    teaching_assistants = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(profile__role='teacher'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Помощники преподавателя'
    )
    class_days_checkboxes = forms.MultipleChoiceField(
        choices=CLASS_WEEKDAY_CHOICES,
        required=False,
        label='Дни занятий',
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = Course
        fields = [
            'title', 
            'description', 
            'short_description', 
            'status',
            'class_time',
            'start_date', 
            'end_date',
            'is_public',
            'allow_self_enrollment',
            'max_students',
            'cover_image',
            'teaching_assistants',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'class_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10:00-11:30'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_self_enrollment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self._course_form_user = user
        super().__init__(*args, **kwargs)
        self.fields["teaching_assistants"].label_from_instance = (
            lambda obj: obj.get_full_name() or obj.get_username()
        )
        ta_qs = self.fields["teaching_assistants"].queryset
        if self.instance.pk and self.instance.instructor_id:
            ta_qs = ta_qs.exclude(pk=self.instance.instructor_id)
        if user is not None and not self.instance.pk:
            ta_qs = ta_qs.exclude(pk=user.pk)
        self.fields["teaching_assistants"].queryset = ta_qs
        if self.instance and self.instance.pk and self.instance.class_days:
            self.fields["class_days_checkboxes"].initial = _tokens_from_class_days_string(
                self.instance.class_days
            )

    def clean_teaching_assistants(self):
        assistants = list(self.cleaned_data.get("teaching_assistants") or [])
        drop = set()
        if self.instance.pk and self.instance.instructor_id:
            drop.add(self.instance.instructor_id)
        if self._course_form_user is not None and not self.instance.pk:
            drop.add(self._course_form_user.pk)
        if drop:
            assistants = [a for a in assistants if a.pk not in drop]
        return assistants

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "Дата окончания не может быть раньше даты начала")

        selected = cleaned_data.get("class_days_checkboxes") or []
        cleaned_data["class_days"] = _class_days_string_from_tokens(selected)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.class_days = self.cleaned_data.get("class_days", "")
        if commit:
            instance.save()
            self.save_m2m()
        return instance


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

    email = forms.EmailField(
        label="Электронная почта",
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "custom-input",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        ),
        help_text="Указывается в учётной записи; используется для уведомлений и восстановления доступа.",
    )

    class Meta:
        model = UserProfile
        fields = ['access_class', 'department', 'position', 'student_group', 'phone', 'avatar']
        widgets = {
            'access_class': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'student_group': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and getattr(self.instance, "user_id", None):
            self.fields["email"].initial = (self.instance.user.email or "").strip()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return ""
        user = self.instance.user
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise ValidationError("Этот адрес почты уже привязан к другой учётной записи.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            user = profile.user
            user.email = self.cleaned_data.get("email") or ""
            user.save(update_fields=["email"])
        return profile

class CourseEnrollmentRequestForm(forms.ModelForm):
    """Форма для подачи заявки на запись на курс"""
    class Meta:
        model = CourseEnrollmentRequest
        fields = ['motivation']
        widgets = {
            'motivation': forms.Textarea(
                attrs={
                    'class': 'custom-textarea',
                    'rows': 5,
                    'placeholder': 'Расскажите, почему вы хотите записаться на этот курс и что планируете получить от обучения…',
                }
            ),
        }

class CourseEnrollmentReviewForm(forms.ModelForm):
    """Форма для рассмотрения заявки на запись на курс"""
    class Meta:
        model = CourseEnrollmentRequest
        fields = ['status', 'review_comment']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AssignmentFileReviewForm(forms.ModelForm):
    """Форма для проверки файла задания преподавателем"""
    class Meta:
        model = AssignmentFileReview
        fields = ['status', 'feedback', 'points']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class AssignmentGradeManageForm(forms.Form):
    """Форма для управления оценками студентов по заданию"""
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    student_name = forms.CharField(widget=forms.HiddenInput(), required=False)
    score = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'style': 'width: 80px;'
        })
    )
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'rows': 2,
            'placeholder': 'Комментарий...'
        })
    )
    status = forms.ChoiceField(
        choices=AssignmentSubmission.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )


class ManagementCourseForm(forms.ModelForm):
    instructor = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='teacher'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Преподаватель',
    )
    class_days_checkboxes = forms.MultipleChoiceField(
        choices=CLASS_WEEKDAY_CHOICES,
        required=False,
        label='Дни занятий',
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = Course
        fields = [
            'title',
            'description',
            'short_description',
            'status',
            'class_time',
            'start_date',
            'end_date',
            'is_public',
            'allow_self_enrollment',
            'max_students',
            'instructor',
            'teaching_assistants',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'class_time': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_self_enrollment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'teaching_assistants': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.class_days:
            self.fields["class_days_checkboxes"].initial = _tokens_from_class_days_string(
                self.instance.class_days
            )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "Дата окончания не может быть раньше даты начала")
        selected = cleaned_data.get("class_days_checkboxes") or []
        cleaned_data["class_days"] = _class_days_string_from_tokens(selected)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.class_days = self.cleaned_data.get("class_days", "")
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ManagementAssignmentForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Курс',
    )

    class Meta:
        model = Assignment
        fields = [
            'course',
            'title',
            'description',
            'due_date',
            'assignment_type',
            'quiz_mode',
            'max_points',
            'passing_score',
            'is_group_assignment',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'assignment_type': forms.Select(attrs={'class': 'form-select'}),
            'quiz_mode': forms.Select(attrs={'class': 'form-select'}),
            'max_points': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_group_assignment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ManagementUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Пароль (только для создания/смены)',
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Роль',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, 'profile'):
            self.fields['role'].initial = self.instance.profile.role

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk and not cleaned_data.get('password'):
            self.add_error('password', 'Пароль обязателен при создании пользователя')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile = getattr(user, 'profile', None)
            if profile:
                profile.role = self.cleaned_data['role']
                profile.save(update_fields=['role'])
        return user