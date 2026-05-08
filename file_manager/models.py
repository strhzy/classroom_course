from django.apps import apps
from django.db import models 
from django.contrib.auth.models import User 
from django.utils import timezone 
import os 
from django.core.exceptions import ValidationError 
from django.utils.html import format_html 

def file_upload_path(instance ,filename ):
    ext =filename.split('.')[-1 ].lower()
    timestamp =timezone.now().strftime('%Y%m%d_%H%M%S')
    filename =f"{instance.title.replace(' ','_')}_{timestamp }.{ext }"
    return os.path.join('files',str(instance.uploaded_by.id ),filename )

class Tag(models.Model ):
    name =models.CharField(max_length =50 ,unique =True )
    color =models.CharField(max_length =7 ,default ='#3498db')

    class Meta :
        ordering =['name']
        verbose_name ='Тег'
        verbose_name_plural ='Теги'

    def __str__(self ):
        return self.name 

    def _safe_hex_color(self ):
        c =(self.color or '#3498db').strip()
        if len(c )==7 and c[0 ]=='#'and all(ch in '0123456789abcdefABCDEF' for ch in c[1:]):
            return c 
        return '#3498db'

    def _badge_attrs_html(self ,*,extra_classes ='',small_font =False ):
        c =self._safe_hex_color()
        classes ='badge rounded-pill'+(f' {extra_classes}'.rstrip() if extra_classes else '')
        font_rule ='font-size:0.75rem;' if small_font else ''
        return format_html(
            'class="{}" style="background:{}22;color:{};border:1px solid {}55;{}"',
            classes ,c ,c ,c ,font_rule ,
        )

    def badge_attrs_list(self ):
        return self._badge_attrs_html(small_font =True )

    def badge_attrs_detail(self ):
        return self._badge_attrs_html(extra_classes ='me-1')

    def filter_swatch_attrs(self ):
        return format_html('style="background-color:{};"', self._safe_hex_color())

class FileCategory(models.Model ):
    name =models.CharField(max_length =100 )
    description =models.TextField(blank =True )
    icon =models.CharField(max_length =50 ,default ='📄')
    order =models.IntegerField(default =0 )

    class Meta :
        ordering =['order','name']
        verbose_name ='Категория файлов'
        verbose_name_plural ='Категории файлов'

    def __str__(self ):
        return self.name 

class File(models.Model ):
    STORAGE_PROVIDER_CHOICES = [
        ("local", "Local"),
        ("yandex_disk", "Yandex Disk"),
    ]
    IMPORTANCE_CHOICES = [
        ("main", "Основное"),
        ("important", "Важное"),
        ("secondary", "Второстепенное"),
    ]
    FILE_TYPE_CHOICES =[
   ('pdf','PDF Document'),
   ('txt','Text File'),
   ('docx','Word Document'),
   ('xlsx','Excel Spreadsheet'),
   ('pptx','PowerPoint Presentation'),
   ('jpg','JPEG Image'),
   ('png','PNG Image'),
   ('mp4','Video MP4'),
   ('mp3','Audio MP3'),
   ('zip','Archive ZIP'),
   ('other','Other'),
    ]

    VISIBILITY_CHOICES =[
   ('private','Private - Только я'),
   ('shared','Shared - С определенными пользователями'),
   ('public','Public - Все пользователи'),
    ]

    title =models.CharField(max_length =255 )
    description =models.TextField(blank =True )
    file =models.FileField(upload_to =file_upload_path, null=True, blank=True)
    file_type =models.CharField(max_length =10 ,choices =FILE_TYPE_CHOICES ,default ='other')
    file_size =models.BigIntegerField(default =0 )
    storage_provider = models.CharField(max_length=20, choices=STORAGE_PROVIDER_CHOICES, default="local")
    yandex_path = models.CharField(max_length=1024, blank=True, default="")

    uploaded_by =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='uploaded_files'
    )
    uploaded_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )
    version =models.IntegerField(default =1 )

    category =models.ForeignKey(
    FileCategory ,
    on_delete =models.SET_NULL ,
    null =True ,
    blank =True ,
    related_name ='files'
    )
    tags =models.ManyToManyField(Tag ,blank =True ,related_name ='files')
    folder =models.ForeignKey(
    'self',
    on_delete =models.CASCADE ,
    null =True ,
    blank =True ,
    related_name ='subfiles',
    limit_choices_to ={'is_folder':True }
    )
    is_folder =models.BooleanField(default =False )

    visibility =models.CharField(
    max_length =10 ,
    choices =VISIBILITY_CHOICES ,
    default ='private'
    )
    shared_with =models.ManyToManyField(
    User ,
    blank =True ,
    related_name ='shared_files'
    )

    extracted_text =models.TextField(blank =True ,null =True )
    has_preview =models.BooleanField(default =False )

    favorite =models.ManyToManyField(
    User ,
    blank =True ,
    related_name ='favorite_files'
    )
    download_count =models.IntegerField(default =0 )
    importance = models.CharField(max_length=20, choices=IMPORTANCE_CHOICES, default="main")

    class Meta :
        ordering =['-uploaded_at']
        verbose_name ='Файл'
        verbose_name_plural ='Файлы'
        indexes =[
        models.Index(fields =['uploaded_by','-uploaded_at']),
        models.Index(fields =['file_type']),
        models.Index(fields =['visibility']),
        models.Index(fields =['extracted_text']),
        ]

    def __str__(self ):
        return self.title 

    def save(self ,*args ,**kwargs ):
        if not self.is_folder:
            ext = self._detect_extension_for_metadata()
            file_type_mapping ={
            'pdf':'pdf',
            'txt':'txt',
            'docx':'docx','doc':'docx',
            'xlsx':'xlsx','xls':'xlsx',
            'pptx':'pptx','ppt':'pptx',
            'jpg':'jpg','jpeg':'jpg',
            'png':'png',
            'mp4':'mp4',
            'mp3':'mp3',
            'zip':'zip','rar':'zip','7z':'zip',
            }
            if ext:
                self.file_type =file_type_mapping.get(ext ,'other')

            if self.file:
                try :
                    self.file_size =self.file.size 
                except :
                    pass 

        super().save(*args ,**kwargs )

    def _detect_extension_for_metadata(self):
        candidates = []
        if self.file and getattr(self.file, "name", ""):
            candidates.append(self.file.name)
        if self.title:
            candidates.append(self.title)
        if self.yandex_path:
            candidates.append(self.yandex_path.split("/")[-1])
        for value in candidates:
            if "." in value:
                return value.rsplit(".", 1)[-1].lower()
        return ""

    def get_file_size_display(self ):
        if self.is_folder :
            return self.get_folder_size_display()

        size =self.file_size 
        for unit in ['B','KB','MB','GB']:
            if size <1024.0 :
                return f"{size :.2f} {unit }"
            size /=1024.0 
        return f"{size :.2f} TB"

    def get_folder_size_display(self ):
        if not self.is_folder :
            return self.get_file_size_display()

        total_size =sum(f.file_size for f in self.subfiles.all()if not f.is_folder )
        size =total_size 
        for unit in ['B','KB','MB','GB']:
            if size <1024.0 :
                return f"{size :.2f} {unit }"
            size /=1024.0 
        return f"{size :.2f} TB"

    def get_file_count(self ):
        if not self.is_folder :
            return 0 
        return self.subfiles.count()

    def can_access(self ,user ):
        profile = getattr(user, "profile", None)
        role = getattr(profile, "role", "")
        if user.is_superuser or user.is_staff or role in {"admin", "staff"}:
            return True

        if self.uploaded_by ==user :
            return True 

        if self.visibility =='public':
            return True 

        if self.visibility =='shared'and user in self.shared_with.all():
            return True 

        # Файл как вложение к решению задания — доступ у преподавателя/ассистента курса
        try:
            AssignmentFile = apps.get_model("classroom_core", "AssignmentFile")
        except LookupError:
            return False
        for af in AssignmentFile.objects.filter(file=self).select_related("assignment"):
            if af.assignment.can_grade(user):
                return True

        return False 

    def can_edit(self ,user ):
        return self.uploaded_by ==user or user.is_superuser 

    def can_delete(self ,user ):
        return self.uploaded_by ==user or user.is_superuser or user.is_staff 

    def is_shared(self):
        return self.visibility == "shared" or self.shared_with.exists()

    def increment_download(self ):
        self.download_count +=1 
        self.save(update_fields =['download_count'])

    def add_to_favorites(self ,user ):
        self.favorite.add(user )

    def remove_from_favorites(self ,user ):
        self.favorite.remove(user )

    def is_favorite(self ,user ):
        return user in self.favorite.all()

    def get_icon(self ):
        icon_mapping ={
        'pdf':'📄',
        'txt':'📝',
        'docx':'📑',
        'xlsx':'📊',
        'pptx':'📽️',
        'jpg':'🖼️',
        'png':'🖼️',
        'mp4':'🎬',
        'mp3':'🎵',
        'zip':'📁',
        'other':'📎',
        }
        return icon_mapping.get(self.file_type ,'📎')

    def get_extension(self ):
        ext = self._detect_extension_for_metadata()
        return ext.upper() if ext else ''

class FileComment(models.Model ):
    file =models.ForeignKey(
    File ,
    on_delete =models.CASCADE ,
    related_name ='comments'
    )
    author =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='file_comments'
    )
    content =models.TextField()
    created_at =models.DateTimeField(auto_now_add =True )
    updated_at =models.DateTimeField(auto_now =True )
    parent =models.ForeignKey(
    'self',
    on_delete =models.CASCADE ,
    null =True ,
    blank =True ,
    related_name ='replies'
    )

    class Meta :
        ordering =['created_at']
        verbose_name ='Комментарий к файлу'
        verbose_name_plural ='Комментарии к файлам'

    def __str__(self ):
        return f"Comment by {self.author.username } on {self.file.title }"

    def can_edit(self ,user ):
        return self.author ==user or user.is_superuser 

    def can_delete(self ,user ):
        return self.author ==user or self.file.uploaded_by ==user or user.is_superuser 

class FileVersion(models.Model ):
    file =models.ForeignKey(
    File ,
    on_delete =models.CASCADE ,
    related_name ='versions'
    )
    version_file =models.FileField(upload_to ='file_versions/', null=True, blank=True)
    version_number =models.IntegerField()
    changed_by =models.ForeignKey(
    User ,
    on_delete =models.SET_NULL ,
    null =True ,
    related_name ='file_versions'
    )
    change_description =models.TextField(blank =True )
    snapshot_title = models.CharField(max_length=255, blank=True, default="")
    snapshot_size = models.BigIntegerField(default=0)
    snapshot_storage_provider = models.CharField(max_length=20, blank=True, default="")
    snapshot_storage_path = models.CharField(max_length=1024, blank=True, default="")
    has_blob = models.BooleanField(default=False)
    blob_storage_provider = models.CharField(max_length=20, blank=True, default="")
    blob_storage_path = models.CharField(max_length=1024, blank=True, default="")
    blob_size = models.BigIntegerField(default=0)
    blob_sha256 = models.CharField(max_length=64, blank=True, default="")
    extracted_text_snapshot = models.TextField(blank=True, default="")
    structured_snapshot = models.JSONField(blank=True, null=True)
    structured_schema_version = models.CharField(max_length=32, blank=True, default="v1")
    created_at =models.DateTimeField(auto_now_add =True )

    class Meta :
        ordering =['-version_number']
        verbose_name ='Версия файла'
        verbose_name_plural ='Версии файлов'

    def __str__(self ):
        return f"Version {self.version_number } of {self.file.title }"

class FileActivity(models.Model ):
    ACTIVITY_TYPES =[
   ('upload','Uploaded'),
   ('download','Downloaded'),
   ('view','Viewed'),
   ('edit','Edited'),
   ('delete','Deleted'),
   ('share','Shared'),
   ('comment','Commented'),
   ('version_create','Created new version'),
   ('favorite_add','Added to favorites'),
   ('favorite_remove','Removed from favorites'),
    ]

    file =models.ForeignKey(
    File ,
    on_delete =models.SET_NULL ,
    null =True ,
    blank =True ,
    related_name ='activities'
    )
    user =models.ForeignKey(
    User ,
    on_delete =models.CASCADE ,
    related_name ='file_activities'
    )
    activity_type =models.CharField(max_length =20 ,choices =ACTIVITY_TYPES )
    description =models.TextField(blank =True )
    created_at =models.DateTimeField(auto_now_add =True )
    ip_address =models.GenericIPAddressField(null =True ,blank =True )

    class Meta :
        ordering =['-created_at']
        verbose_name ='Активность с файлом'
        verbose_name_plural ='Активность с файлами'
        indexes =[
        models.Index(fields =['user','-created_at']),
        models.Index(fields =['activity_type','-created_at']),
        ]

    def __str__(self ):
        return f"{self.user.username } {self.activity_type } {self.file.title if self.file else 'deleted file'}"

    @classmethod 
    def log_activity(cls ,file ,user ,activity_type ,description ="",ip_address =None ):
        return cls.objects.create(
        file =file ,
        user =user ,
        activity_type =activity_type ,
        description =description ,
        ip_address =ip_address 
        )
class UserStorageQuota(models.Model ):
    user =models.OneToOneField(User ,on_delete =models.CASCADE ,related_name ='storage_quota')
    total_quota_bytes =models.BigIntegerField(default =5368709120 )
    used_bytes =models.BigIntegerField(default =0 )
    last_updated =models.DateTimeField(auto_now =True )

    class Meta :
        verbose_name ='Квота хранилища пользователя'
        verbose_name_plural ='Квоты хранилища пользователей'

    def __str__(self ):
        return f"{self.user.username }: {self.used_bytes } / {self.total_quota_bytes } bytes"

    def get_used_percentage(self ):
        if self.total_quota_bytes ==0 :
            return 0.0 
        return(self.used_bytes /self.total_quota_bytes )*100 

    def get_quota_display(self ):
        def format_bytes(bytes_value ):
            for unit in ['B','KB','MB','GB','TB']:
                if bytes_value <1024.0 :
                    return f"{bytes_value :.2f} {unit }"
                bytes_value /=1024.0 
            return f"{bytes_value :.2f} PB"

        return f"{format_bytes(self.used_bytes )} / {format_bytes(self.total_quota_bytes )}"

    def has_enough_space(self ,additional_bytes ):
        return self.used_bytes +additional_bytes <=self.total_quota_bytes 

    def update_usage(self ):
        total_size =File.objects.filter(
        uploaded_by =self.user ,
        is_folder =False 
        ).aggregate(total =models.Sum('file_size'))['total']or 0 
        self.used_bytes =total_size 
        self.save(update_fields =['used_bytes','last_updated'])


class ExternalStorageConnection(models.Model):
    PROVIDER_CHOICES = [
        ("yandex_disk", "Yandex Disk"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_storage_connections")
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, default="yandex_disk")
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "provider"]

    def __str__(self):
        return f"{self.user.username}::{self.provider}"


class FavoriteCollection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_collections")
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "title"]
        ordering = ["title"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class FavoriteCollectionItem(models.Model):
    collection = models.ForeignKey(FavoriteCollection, on_delete=models.CASCADE, related_name="items")
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="favorite_collection_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["collection", "file"]


class SharedWorkspace(models.Model):
    title = models.CharField(max_length=120)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_workspaces")
    participants = models.ManyToManyField(User, related_name="shared_workspaces")
    files = models.ManyToManyField(File, blank=True, related_name="workspaces")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title