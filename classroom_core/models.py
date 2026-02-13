from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator

class Course(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активный'),
        ('archived', 'Архивирован'),
        ('completed', 'Завершен'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True)
    
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
    color = models.CharField(
        max_length=7, 
        default='#3498db'
    )
    code = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True
    )
    
    is_public = models.BooleanField(
        default=False
    )
    allow_self_enrollment = models.BooleanField(
        default=True
    )
    max_students = models.IntegerField(
        null=True, 
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['code']),
        ]
    
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
        
        total_duration = (self.end_date - self.start_date).total_seconds()
        elapsed_duration = (timezone.now() - self.start_date).total_seconds()
        
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
        return user == self.instructor or user.is_superuser
    
    def can_delete(self, user):
        return user == self.instructor or user.is_superuser
    
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

class CourseSection(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='sections'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['course', 'order']
        verbose_name = 'Раздел курса'
        verbose_name_plural = 'Разделы курса'
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class CourseMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ('file', 'Файл'),
        ('link', 'Ссылка'),
        ('video', 'Видео'),
        ('text', 'Текст'),
        ('assignment', 'Задание'),
    ]
    
    section = models.ForeignKey(
        CourseSection, 
        on_delete=models.CASCADE, 
        related_name='materials'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    material_type = models.CharField(
        max_length=20, 
        choices=MATERIAL_TYPE_CHOICES
    )
    
    file = models.FileField(
        upload_to='course_materials/', 
        null=True, 
        blank=True
    )
    files = models.ManyToManyField(
        'file_manager.File',
        blank=True,
        related_name='course_materials'
    )
    
    url = models.URLField(blank=True)
    
    content = models.TextField(blank=True)
    
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['section', 'order']
        verbose_name = 'Учебный материал'
        verbose_name_plural = 'Учебные материалы'
    
    def __str__(self):
        return f"{self.section.title} - {self.title}"

class Assignment(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
        ('closed', 'Закрыто'),
    ]
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    section = models.ForeignKey(
        CourseSection, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assignments'
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft'
    )
    
    due_date = models.DateTimeField(null=True, blank=True)
    allow_late_submissions = models.BooleanField(default=False)
    
    max_points = models.IntegerField(default=100)
    passing_score = models.IntegerField(
        default=50
    )
    
    is_group_assignment = models.BooleanField(default=False)
    group_size_min = models.IntegerField(default=1)
    group_size_max = models.IntegerField(default=1)
    
    attachment = models.FileField(
        upload_to='assignment_attachments/', 
        null=True, 
        blank=True
    )
    files = models.ManyToManyField(
        'file_manager.File',
        blank=True,
        related_name='assignments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-due_date', '-created_at']
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
    
    def __str__(self):
        return self.title
    
    def is_overdue(self):
        if not self.due_date:
            return False
        return timezone.now() > self.due_date
    
    def can_submit(self):
        if self.status != 'published':
            return False
        if self.is_overdue() and not self.allow_late_submissions:
            return False
        return True

class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Отправлено'),
        ('graded', 'Оценено'),
        ('returned', 'Возвращено на доработку'),
    ]
    
    assignment = models.ForeignKey(
        Assignment, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assignment_submissions'
    )
    
    text_response = models.TextField(blank=True)
    file_submission = models.FileField(
        upload_to='assignment_submissions/', 
        null=True, 
        blank=True
    )
    
    group_members = models.ManyToManyField(
        User, 
        blank=True,
        related_name='group_submissions'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='submitted'
    )
    
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='graded_submissions'
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Решение задания'
        verbose_name_plural = 'Решения заданий'
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
    
    def is_late(self):
        if not self.assignment.due_date:
            return False
        return self.submitted_at > self.assignment.due_date
    
    def get_status_display_with_late(self):
        status = self.get_status_display()
        if self.is_late():
            status += " (с опозданием)"
        return status

class Announcement(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='announcements'
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='announcements'
    )
    
    is_pinned = models.BooleanField(
        default=False
    )
    
    send_email_notification = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.published_at and self.pk:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    files = models.ManyToManyField(
        'file_manager.File',
        blank=True,
        related_name='announcements'
    )

class CourseDiscussion(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='discussions'
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='course_discussions'
    )
    
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = 'Обсуждение'
        verbose_name_plural = 'Обсуждения'
    
    def __str__(self):
        return self.title
    
    def get_reply_count(self):
        return self.replies.count()

class DiscussionReply(models.Model):
    discussion = models.ForeignKey(
        CourseDiscussion, 
        on_delete=models.CASCADE, 
        related_name='replies'
    )
    
    content = models.TextField()
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='discussion_replies'
    )
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Ответ на обсуждение'
        verbose_name_plural = 'Ответы на обсуждения'
    
    def __str__(self):
        return f"Reply by {self.author.username}"

class CourseGrade(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='grades'
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='course_grades'
    )
    
    grade = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    letter_grade = models.CharField(
        max_length=2, 
        blank=True
    )
    
    completion_percentage = models.IntegerField(default=0)
    
    comments = models.TextField(blank=True)
    is_passing = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['course', 'student']
        verbose_name = 'Оценка курса'
        verbose_name_plural = 'Оценки курса'
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title}: {self.grade}"
    
    def calculate_letter_grade(self):
        if self.grade is None:
            return ''
        
        grade_value = float(self.grade)
        if grade_value >= 90:
            return 'A'
        elif grade_value >= 80:
            return 'B'
        elif grade_value >= 70:
            return 'C'
        elif grade_value >= 60:
            return 'D'
        else:
            return 'F'

class CourseNotification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('announcement', 'Объявление'),
        ('assignment', 'Задание'),
        ('grade', 'Оценка'),
        ('general', 'Общее'),
    ]
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPE_CHOICES
    )
    
    recipients = models.ManyToManyField(
        User, 
        related_name='course_notifications'
    )
    
    is_read = models.ManyToManyField(
        User, 
        blank=True,
        related_name='read_notifications'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление курса'
        verbose_name_plural = 'Уведомления курса'
    
    def __str__(self):
        return self.title
    
    def mark_as_read(self, user):
        self.is_read.add(user)