from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
from django.conf import settings
from django.db.models import SET_NULL
from classroom_core.models import Course

def file_upload_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{instance.title.replace(' ', '_')}_{timestamp}.{ext}"
    return os.path.join('files', str(instance.uploaded_by.id), filename)

class File(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF Document'),
        ('txt', 'Text File'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel Spreadsheet'),
        ('pptx', 'PowerPoint Presentation'),
        ('jpg', 'JPEG Image'),
        ('png', 'PNG Image'),
        ('mp4', 'Video MP4'),
        ('mp3', 'Audio MP3'),
        ('zip', 'Archive ZIP'),
        ('other', 'Other'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'Private - Только я'),
        ('shared', 'Shared - С определенными пользователями'),
        ('public', 'Public - Все пользователи'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=file_upload_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other')
    file_size = models.BigIntegerField(default=0)
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_files'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    # Привязка к курсу (опционально)
    course = models.ForeignKey(
        Course,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    folder = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subfiles',
        limit_choices_to={'is_folder': True}
    )
    is_folder = models.BooleanField(default=False)
    
    visibility = models.CharField(
        max_length=10, 
        choices=VISIBILITY_CHOICES, 
        default='private'
    )
    shared_with = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='shared_files'
    )
    
    extracted_text = models.TextField(blank=True, null=True)
    has_preview = models.BooleanField(default=False)
    
    favorite = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='favorite_files'
    )
    download_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        indexes = [
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['file_type']),
            models.Index(fields=['visibility']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.file and not self.is_folder:
            ext = self.file.name.split('.')[-1].lower()
            file_type_mapping = {
                'pdf': 'pdf',
                'txt': 'txt',
                'docx': 'docx', 'doc': 'docx',
                'xlsx': 'xlsx', 'xls': 'xlsx',
                'pptx': 'pptx', 'ppt': 'pptx',
                'jpg': 'jpg', 'jpeg': 'jpg',
                'png': 'png',
                'mp4': 'mp4',
                'mp3': 'mp3',
                'zip': 'zip', 'rar': 'zip', '7z': 'zip',
            }
            self.file_type = file_type_mapping.get(ext, 'other')
            
            try:
                self.file_size = self.file.size
            except:
                pass
        
        super().save(*args, **kwargs)
    
    def get_file_size_display(self):
        if self.is_folder:
            return self.get_folder_size_display()
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def get_folder_size_display(self):
        if not self.is_folder:
            return self.get_file_size_display()
        
        total_size = sum(f.file_size for f in self.subfiles.all() if not f.is_folder)
        size = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def get_file_count(self):
        if not self.is_folder:
            return 0
        return self.subfiles.count()
    
    def can_access(self, user):
        if self.uploaded_by == user:
            return True
        
        if self.visibility == 'public':
            return True
        
        if self.visibility == 'shared' and user in self.shared_with.all():
            return True
        
        return False
    
    def can_edit(self, user):
        return self.uploaded_by == user or user.is_superuser
    
    def can_delete(self, user):
        return self.uploaded_by == user or user.is_superuser or user.is_staff
    
    def increment_download(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def add_to_favorites(self, user):
        self.favorite.add(user)
    
    def remove_from_favorites(self, user):
        self.favorite.remove(user)
    
    def is_favorite(self, user):
        return user in self.favorite.all()
    
    def get_icon(self):
        icon_mapping = {
            'pdf': '📄',
            'txt': '📝',
            'docx': '📑',
            'xlsx': '📊',
            'pptx': '📽️',
            'jpg': '🖼️',
            'png': '🖼️',
            'mp4': '🎬',
            'mp3': '🎵',
            'zip': '📁',
            'other': '📎',
        }
        return icon_mapping.get(self.file_type, '📎')
    
    def get_extension(self):
        if not self.file:
            return ''
        return self.file.name.split('.')[-1].upper()

class FileComment(models.Model):
    file = models.ForeignKey(
        File, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='file_comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Комментарий к файлу'
        verbose_name_plural = 'Комментарии к файлам'
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.file.title}"
    
    def can_edit(self, user):
        return self.author == user or user.is_superuser
    
    def can_delete(self, user):
        return self.author == user or self.file.uploaded_by == user or user.is_superuser

class FileVersion(models.Model):
    file = models.ForeignKey(
        File, 
        on_delete=models.CASCADE, 
        related_name='versions'
    )
    version_file = models.FileField(upload_to='file_versions/')
    version_number = models.IntegerField()
    changed_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='file_versions'
    )
    change_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-version_number']
        verbose_name = 'Версия файла'
        verbose_name_plural = 'Версии файлов'
    
    def __str__(self):
        return f"Version {self.version_number} of {self.file.title}"

class FileActivity(models.Model):
    ACTIVITY_TYPES = [
        ('upload', 'Uploaded'),
        ('download', 'Downloaded'),
        ('view', 'Viewed'),
        ('edit', 'Edited'),
        ('delete', 'Deleted'),
        ('share', 'Shared'),
        ('comment', 'Commented'),
    ]
    
    file = models.ForeignKey(
        File, 
        on_delete=models.CASCADE, 
        related_name='activities'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='file_activities'
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Активность с файлом'
        verbose_name_plural = 'Активность с файлами'
    
    def __str__(self):
        return f"{self.user.username} {self.activity_type} {self.file.title}"