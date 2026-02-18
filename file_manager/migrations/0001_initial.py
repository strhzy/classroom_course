

import django .db .models .deletion 
import file_manager .models 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    initial =True 

    dependencies =[
    ('classroom_core','0001_initial'),
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .CreateModel (
    name ='File',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('description',models .TextField (blank =True )),
    ('file',models .FileField (upload_to =file_manager .models .file_upload_path )),
    ('file_type',models .CharField (choices =[('pdf','PDF Document'),('txt','Text File'),('docx','Word Document'),('xlsx','Excel Spreadsheet'),('pptx','PowerPoint Presentation'),('jpg','JPEG Image'),('png','PNG Image'),('mp4','Video MP4'),('mp3','Audio MP3'),('zip','Archive ZIP'),('other','Other')],default ='other',max_length =10 )),
    ('file_size',models .BigIntegerField (default =0 )),
    ('uploaded_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('version',models .IntegerField (default =1 )),
    ('is_folder',models .BooleanField (default =False )),
    ('visibility',models .CharField (choices =[('private','Private - Только я'),('shared','Shared - С определенными пользователями'),('public','Public - Все пользователи')],default ='private',max_length =10 )),
    ('extracted_text',models .TextField (blank =True ,null =True )),
    ('has_preview',models .BooleanField (default =False )),
    ('download_count',models .IntegerField (default =0 )),
    ('course',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='files',to ='classroom_core.course')),
    ('favorite',models .ManyToManyField (blank =True ,related_name ='favorite_files',to =settings .AUTH_USER_MODEL )),
    ('folder',models .ForeignKey (blank =True ,limit_choices_to ={'is_folder':True },null =True ,on_delete =django .db .models .deletion .CASCADE ,related_name ='subfiles',to ='file_manager.file')),
    ('shared_with',models .ManyToManyField (blank =True ,related_name ='shared_files',to =settings .AUTH_USER_MODEL )),
    ('uploaded_by',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='uploaded_files',to =settings .AUTH_USER_MODEL )),
    ],
    options ={
    'verbose_name':'Файл',
    'verbose_name_plural':'Файлы',
    'ordering':['-uploaded_at'],
    },
    ),
    migrations .CreateModel (
    name ='FileActivity',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('activity_type',models .CharField (choices =[('upload','Uploaded'),('download','Downloaded'),('view','Viewed'),('edit','Edited'),('delete','Deleted'),('share','Shared'),('comment','Commented')],max_length =20 )),
    ('description',models .TextField (blank =True )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('ip_address',models .GenericIPAddressField (blank =True ,null =True )),
    ('file',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='activities',to ='file_manager.file')),
    ('user',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='file_activities',to =settings .AUTH_USER_MODEL )),
    ],
    options ={
    'verbose_name':'Активность с файлом',
    'verbose_name_plural':'Активность с файлами',
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='FileComment',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('content',models .TextField ()),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('author',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='file_comments',to =settings .AUTH_USER_MODEL )),
    ('file',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='comments',to ='file_manager.file')),
    ('parent',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .CASCADE ,related_name ='replies',to ='file_manager.filecomment')),
    ],
    options ={
    'verbose_name':'Комментарий к файлу',
    'verbose_name_plural':'Комментарии к файлам',
    'ordering':['created_at'],
    },
    ),
    migrations .CreateModel (
    name ='FileVersion',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('version_file',models .FileField (upload_to ='file_versions/')),
    ('version_number',models .IntegerField ()),
    ('change_description',models .TextField (blank =True )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('changed_by',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='file_versions',to =settings .AUTH_USER_MODEL )),
    ('file',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='versions',to ='file_manager.file')),
    ],
    options ={
    'verbose_name':'Версия файла',
    'verbose_name_plural':'Версии файлов',
    'ordering':['-version_number'],
    },
    ),
    migrations .AddIndex (
    model_name ='file',
    index =models .Index (fields =['uploaded_by','-uploaded_at'],name ='file_manage_uploade_b38260_idx'),
    ),
    migrations .AddIndex (
    model_name ='file',
    index =models .Index (fields =['file_type'],name ='file_manage_file_ty_be8bdc_idx'),
    ),
    migrations .AddIndex (
    model_name ='file',
    index =models .Index (fields =['visibility'],name ='file_manage_visibil_a1c744_idx'),
    ),
    ]
