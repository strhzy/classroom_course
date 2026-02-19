from django.db import models 
from django.contrib.auth.models import User ,AbstractUser 
from django.utils import timezone 
from django.core.validators import FileExtensionValidator 

class StudentGroup(models.Model):
    """Модель группы студентов"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_groups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Группа студентов'
        verbose_name_plural = 'Группы студентов'
    
    def __str__(self):
        return self.name
    
    def get_student_count(self):
        return self.students.count()

class UserProfile(models.Model):
    """Профиль пользователя с ролями"""
    
    ROLE_CHOICES = [
       ('student', 'Студент'),
       ('teacher', 'Преподаватель'),
       ('staff', 'Сотрудник учебной части'),
       ('admin', 'Администратор'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    student_group = models.ForeignKey(
        StudentGroup, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='students'
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_staff(self):
        return self.role == 'staff'
    
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser

class Course(models.Model):
    """Модель курса"""
    
    STATUS_CHOICES = [
       ('draft', 'Черновик'),
       ('active', 'Активный'),
       ('archived', 'Архивирован'),
       ('completed', 'Завершен'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    
    instructor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='courses_created'
    )
    teaching_assistants = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='courses_assisting'
    )
    students = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='courses_enrolled'
    )
    student_groups = models.ManyToManyField(
        StudentGroup,
        blank=True,
        related_name='courses_enrolled',
        help_text='Группы студентов, зачисленные на курс'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft'
    )
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    cover_image = models.ImageField(
        upload_to='course_covers/', 
        null=True, 
        blank=True
    )
    color = models.CharField(max_length=7, default='#3498db')
    
    is_public = models.BooleanField(default=False)
    allow_self_enrollment = models.BooleanField(default=True)
    max_students = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.code and not self.pk:
            from django.utils.crypto import get_random_string
            self.code = f"COURSE-{get_random_string(6).upper()}"
        
        if self.status == 'active' and self.end_date and self.end_date < timezone.now():
            self.status = 'completed'
        
        super().save(*args, **kwargs)
    
    def get_student_count(self):
        return self.students.count()
    
    def get_progress(self):
        if not self.start_date or not self.end_date:
            return 0
        
        total_duration =(self.end_date - self.start_date).total_seconds()
        elapsed_duration =(timezone.now() - self.start_date).total_seconds()
        
        if elapsed_duration <= 0:
            return 0
        if elapsed_duration >= total_duration:
            return 100
        
        return int((elapsed_duration / total_duration) * 100)
    
    def can_access(self, user):
        if user.is_superuser:
            return True
        if user == self.instructor:
            return True
        if user in self.teaching_assistants.all():
            return True
        if user in self.students.all():
            return True
        if self.is_public and self.status == 'active':
            return True
        return False
    
    def can_edit(self, user):
        return user == self.instructor or user.is_superuser or user.profile.is_staff()
    
    def can_delete(self, user):
        return user == self.instructor or user.is_superuser or user.profile.is_staff()
    
    def add_student(self, user):
        if self.max_students and self.get_student_count() >= self.max_students:
            return False, "Достигнуто максимальное количество студентов"
        
        if user in self.students.all():
            return False, "Пользователь уже записан на курс"
        
        self.students.add(user)
        return True, "Студент успешно добавлен"
    
    def remove_student(self, user):
        if user not in self.students.all():
            return False, "Пользователь не записан на курс"
        
        self.students.remove(user)
        return True, "Студент успешно удален"
    
    def add_student_group(self, group):
        """Добавление всей группы студентов на курс"""
        if group in self.student_groups.all():
            return False, "Группа уже добавлена на курс"
        
        self.student_groups.add(group)
        
        students_added = 0
        for student_profile in group.students.all():
            if student_profile.user not in self.students.all():
                success, message = self.add_student(student_profile.user)
                if success:
                    students_added += 1
        
        return True, f"Группа '{group.name}' добавлена на курс. Зачислено {students_added} студентов"
    
    def remove_student_group(self, group):
        """Удаление группы студентов с курса"""
        if group not in self.student_groups.all():
            return False, "Группа не найдена на курсе"
        
        self.student_groups.remove(group)
        
        return True, f"Группа '{group.name}' удалена с курса"
    
    def get_all_enrolled_students(self):
        """Получить всех студентов, зачисленных на курс(индивидуально + через группы)"""
        individual_students = set(self.students.all())
        group_students = set()
        
        for group in self.student_groups.all():
            for profile in group.students.all():
                group_students.add(profile.user)
        
        return individual_students.union(group_students)

class CourseSection(models.Model ):
    """Раздел курса(например, 'Неделя 1', 'Тема 1')"""

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='sections'
    )
    title =models.CharField(max_length =255 )
    description =models.TextField(blank =True )
    order =models.IntegerField(default =0 )
    is_visible =models.BooleanField(default =True )

    class Meta :
        ordering =['course','order']
        verbose_name ='Раздел курса'
        verbose_name_plural ='Разделы курса'

    def __str__(self ):
        return f"{self.course.title } - {self.title }"

class CourseMaterial(models.Model ):
    """Учебные материалы курса"""

    MATERIAL_TYPE_CHOICES =[
   ('file','Файл'),
   ('link','Ссылка'),
   ('video','Видео'),
   ('text','Текст'),
   ('assignment','Задание'),
    ]

    section =models.ForeignKey(
    CourseSection ,
    on_delete =models.CASCADE ,
    related_name ='materials'
    )
    title =models.CharField(max_length =255 )
    description =models.TextField(blank =True )

    material_type =models.CharField(
    max_length =20 ,
    choices =MATERIAL_TYPE_CHOICES 
    )

    file =models.FileField(
    upload_to ='course_materials/',
    null =True ,
    blank =True ,
    validators =[FileExtensionValidator(allowed_extensions =['pdf','docx','xlsx','pptx','txt','zip','jpg','png','mp4','mp3'])]
    )

    url =models.URLField(blank =True )

    content =models.TextField(blank =True )

    order =models.IntegerField(default =0 )
    is_visible =models.BooleanField(default =True )
    is_required =models.BooleanField(default =False )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['section','order']
        verbose_name ='Учебный материал'
        verbose_name_plural ='Учебные материалы'

    def __str__(self ):
        return f"{self.section.title } - {self.title }"

class Assignment(models.Model ):
    """Задание курса"""

    STATUS_CHOICES =[
   ('draft','Черновик'),
   ('published','Опубликовано'),
   ('closed','Закрыто'),
    ]

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='assignments'
    )
    section =models.ForeignKey(
    CourseSection ,
    on_delete =models.SET_NULL ,
    null =True ,
    blank =True ,
    related_name ='assignments'
    )

    title =models.CharField(max_length =255 )
    description =models.TextField()

    status =models.CharField(
    max_length =20 ,
    choices =STATUS_CHOICES ,
    default ='draft'
    )

    due_date =models.DateTimeField(null =True ,blank =True )
    allow_late_submissions =models.BooleanField(default =False )

    max_points =models.IntegerField(default =100 )
    passing_score =models.IntegerField(default =50 )

    is_group_assignment =models.BooleanField(default =False )
    group_size_min =models.IntegerField(default =1 )
    group_size_max =models.IntegerField(default =1 )

    attachment =models.FileField(
    upload_to ='assignment_attachments/',
    null =True ,
    blank =True 
    )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )
    published_at =models.DateTimeField(null =True ,blank =True )

    class Meta :
        ordering =['-due_date','-created_at']
        verbose_name ='Задание'
        verbose_name_plural ='Задания'

    def __str__(self ):
        return self.title 

    def is_overdue(self ):
        if not self.due_date :
            return False 
        return timezone.now()>self.due_date 

    def can_submit(self ):
        if self.status !='published':
            return False 
        if self.is_overdue()and not self.allow_late_submissions :
            return False 
        return True 

    def can_grade(self ,user ):
        """Проверка, может ли пользователь оценивать задание"""
        return user ==self.course.instructor or user in self.course.teaching_assistants.all()or user.is_superuser or user.profile.is_staff()

class AssignmentSubmission(models.Model ):
    """Решение задания от студента"""

    STATUS_CHOICES =[
   ('submitted','Отправлено'),
   ('graded','Оценено'),
   ('returned','Возвращено на доработку'),
    ]

    assignment =models.ForeignKey(
    Assignment ,
    on_delete =models.CASCADE ,
    related_name ='submissions'
    )
    student =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='assignment_submissions'
    )

    text_response =models.TextField(blank =True )
    file_submission =models.FileField(
    upload_to ='assignment_submissions/',
    null =True ,
    blank =True 
    )

    group_members =models.ManyToManyField(
    User ,
    blank =True ,
    related_name ='group_submissions'
    )

    status =models.CharField(
    max_length =20 ,
    choices =STATUS_CHOICES ,
    default ='submitted'
    )

    score =models.IntegerField(null =True ,blank =True )
    feedback =models.TextField(blank =True )
    graded_by =models.ForeignKey(
    User ,
    on_delete =models.SET_NULL ,
    null =True ,
    blank =True ,
    related_name ='graded_submissions'
    )
    graded_at =models.DateTimeField(null =True ,blank =True )

    submitted_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['-submitted_at']
        verbose_name ='Решение задания'
        verbose_name_plural ='Решения заданий'
        unique_together =['assignment','student']

    def __str__(self ):
        return f"{self.student.username } - {self.assignment.title }"

    def is_late(self ):
        if not self.assignment.due_date :
            return False 
        return self.submitted_at >self.assignment.due_date 

    def get_status_display_with_late(self ):
        status =self.get_status_display()
        if self.is_late():
            status +="(с опозданием)"
        return status 

    def can_view(self ,user ):
        """Проверка, может ли пользователь просматривать решение"""
        return user ==self.student or self.assignment.can_grade(user )

    def can_grade(self ,user ):
        """Проверка, может ли пользователь оценивать решение"""
        return self.assignment.can_grade(user )

class Announcement(models.Model ):
    """Объявление в курсе"""

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='announcements'
    )

    title =models.CharField(max_length =255 )
    content =models.TextField()

    author =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='announcements'
    )

    is_pinned =models.BooleanField(default =False )
    send_email_notification =models.BooleanField(default =False )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )
    published_at =models.DateTimeField(null =True ,blank =True )

    class Meta :
        ordering =['-is_pinned','-created_at']
        verbose_name ='Объявление'
        verbose_name_plural ='Объявления'

    def __str__(self ):
        return self.title 

    def save(self ,*args ,**kwargs ):
        if not self.published_at and self.pk :
            self.published_at =timezone.now()
        super().save(*args ,**kwargs )

    def can_edit(self ,user ):
        """Проверка, может ли пользователь редактировать объявление"""
        return user ==self.author or user ==self.course.instructor or user.is_superuser or user.profile.is_staff()

class CourseDiscussion(models.Model ):
    """Обсуждение в курсе"""

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='discussions'
    )

    title =models.CharField(max_length =255 )
    content =models.TextField()

    author =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='course_discussions'
    )

    is_pinned =models.BooleanField(default =False )
    is_locked =models.BooleanField(default =False )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['-is_pinned','-created_at']
        verbose_name ='Обсуждение'
        verbose_name_plural ='Обсуждения'

    def __str__(self ):
        return self.title 

    def get_reply_count(self ):
        return self.replies.count()

    def can_edit(self ,user ):
        """Проверка, может ли пользователь редактировать обсуждение"""
        return user ==self.author or user ==self.course.instructor or user.is_superuser or user.profile.is_staff()

class DiscussionReply(models.Model ):
    """Ответ на обсуждение"""

    discussion =models.ForeignKey(
    CourseDiscussion ,
    on_delete =models.CASCADE ,
    related_name ='replies'
    )

    content =models.TextField()
    author =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='discussion_replies'
    )

    parent =models.ForeignKey(
    'self',
    on_delete =models.CASCADE ,
    null =True ,
    blank =True ,
    related_name ='replies'
    )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['created_at']
        verbose_name ='Ответ на обсуждение'
        verbose_name_plural ='Ответы на обсуждения'

    def __str__(self ):
        return f"Reply by {self.author.username }"

    def can_edit(self ,user ):
        """Проверка, может ли пользователь редактировать ответ"""
        return user ==self.author or user ==self.discussion.course.instructor or user.is_superuser or user.profile.is_staff()

class CourseGrade(models.Model ):
    """Оценка студента по курсу"""

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='grades'
    )
    student =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='course_grades'
    )

    grade =models.DecimalField(
    max_digits =5 ,
    decimal_places =2 ,
    null =True ,
    blank =True 
    )

    letter_grade =models.CharField(
    max_length =2 ,
    blank =True 
    )

    completion_percentage =models.IntegerField(default =0 )

    comments =models.TextField(blank =True )
    is_passing =models.BooleanField(default =False )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        unique_together =['course','student']
        verbose_name ='Оценка курса'
        verbose_name_plural ='Оценки курса'

    def __str__(self ):
        return f"{self.student.username } - {self.course.title }: {self.grade }"

    def calculate_letter_grade(self ):
        if self.grade is None :
            return ''

        grade_value =float(self.grade )
        if grade_value >=90 :
            return 'A'
        elif grade_value >=80 :
            return 'B'
        elif grade_value >=70 :
            return 'C'
        elif grade_value >=60 :
            return 'D'
        else :
            return 'F'

class CourseNotification(models.Model ):
    """Уведомления курса"""

    NOTIFICATION_TYPE_CHOICES =[
   ('announcement','Объявление'),
   ('assignment','Задание'),
   ('grade','Оценка'),
   ('general','Общее'),
    ]

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='notifications'
    )

    title =models.CharField(max_length =255 )
    message =models.TextField()
    notification_type =models.CharField(
    max_length =20 ,
    choices =NOTIFICATION_TYPE_CHOICES
    )

    recipients =models.ManyToManyField(
    User ,
    related_name ='course_notifications'
    )

    is_read =models.ManyToManyField(
    User ,
    blank =True ,
    related_name ='read_notifications'
    )

    created_at =models.DateTimeField(auto_now_add =True )

    class Meta :
        ordering =['-created_at']
        verbose_name ='Уведомление курса'
        verbose_name_plural ='Уведомления курса'

    def __str__(self ):
        return self.title

    def mark_as_read(self ,user ):
        self.is_read.add(user )


class CourseEnrollmentRequest(models.Model ):
    """Заявка студента на запись на курс"""

    STATUS_CHOICES =[
   ('pending','На рассмотрении'),
   ('approved','Одобрена'),
   ('rejected','Отклонена'),
    ]

    course =models.ForeignKey(
    Course ,
    on_delete =models.CASCADE ,
    related_name ='enrollment_requests'
    )
    student =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='course_enrollment_requests'
    )

    status =models.CharField(
    max_length =20 ,
    choices =STATUS_CHOICES ,
    default ='pending'
    )

    motivation =models.TextField(
    blank =True ,
    help_text ='Расскажите, почему вы хотите записаться на этот курс'
    )

    reviewed_by =models.ForeignKey(
    User ,
    on_delete =models.SET_NULL ,
    null =True ,
    blank =True ,
    related_name ='reviewed_enrollment_requests'
    )
    review_comment =models.TextField(
    blank =True ,
    help_text ='Комментарий преподавателя к решению'
    )

    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )
    reviewed_at =models.DateTimeField(null =True ,blank =True )

    class Meta :
        ordering =['-created_at']
        verbose_name ='Заявка на запись на курс'
        verbose_name_plural ='Заявки на запись на курсы'
        unique_together =['course','student']

    def __str__(self ):
        return f"{self.student.username } - {self.course.title }({self.get_status_display()})"

    def can_review(self ,user ):
        """Проверка, может ли пользователь рассмотреть заявку"""
        return user ==self.course.instructor or user.is_superuser or user.profile.is_staff()


class AssignmentFile(models.Model ):
    """Файл, прикрепленный к заданию студентом"""

    assignment =models.ForeignKey(
    Assignment ,
    on_delete =models.CASCADE ,
    related_name ='files'
    )
    student =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='assignment_files'
    )

    file =models.ForeignKey(
    'file_manager.File',
    on_delete =models.CASCADE ,
    related_name ='assignment_submissions',
    help_text ='Файл из файлового хранилища'
    )

    description =models.TextField(
    blank =True ,
    help_text ='Описание файла(опционально)'
    )

    uploaded_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['-uploaded_at']
        verbose_name ='Файл задания'
        verbose_name_plural ='Файлы заданий'

    def __str__(self ):
        return f"{self.file.title } - {self.student.username }({self.assignment.title })"

    def can_delete(self ,user ):
        """Проверка, может ли пользователь удалить файл"""
        return user ==self.student or self.assignment.can_grade(user )


class AssignmentFileReview(models.Model ):
    """Проверка файла задания преподавателем"""

    STATUS_CHOICES =[
   ('pending','На проверке'),
   ('approved','Принят'),
   ('rejected','Отклонен'),
   ('needs_revision','Требует доработки'),
    ]

    file =models.ForeignKey(
    AssignmentFile ,
    on_delete =models.CASCADE ,
    related_name ='reviews'
    )
    reviewer =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='file_reviews'
    )

    status =models.CharField(
    max_length =20 ,
    choices =STATUS_CHOICES ,
    default ='pending'
    )

    feedback =models.TextField(
    blank =True ,
    help_text ='Комментарий преподавателя к файлу'
    )

    points =models.IntegerField(
    null =True ,
    blank =True ,
    help_text ='Баллы за файл(опционально)'
    )

    reviewed_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )

    class Meta :
        ordering =['-reviewed_at']
        verbose_name ='Проверка файла'
        verbose_name_plural ='Проверки файлов'
        unique_together =['file','reviewer']

    def __str__(self ):
        return f"Проверка {self.file.file.name } от {self.reviewer.username }({self.get_status_display()})"

    def can_review(self ,user ):
        """Проверка, может ли пользователь проверить файл"""
        return self.file.assignment.can_grade(user )