

import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    dependencies =[
    ('file_manager','0001_initial'),
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .CreateModel (
    name ='FileCategory',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('name',models .CharField (max_length =100 )),
    ('description',models .TextField (blank =True )),
    ('icon',models .CharField (default ='📄',max_length =50 )),
    ('order',models .IntegerField (default =0 )),
    ],
    options ={
    'verbose_name':'Категория файлов',
    'verbose_name_plural':'Категории файлов',
    'ordering':['order','name'],
    },
    ),
    migrations .CreateModel (
    name ='Tag',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('name',models .CharField (max_length =50 ,unique =True )),
    ('color',models .CharField (default ='#3498db',max_length =7 )),
    ],
    options ={
    'verbose_name':'Тег',
    'verbose_name_plural':'Теги',
    'ordering':['name'],
    },
    ),
    migrations .CreateModel (
    name ='UserStorageQuota',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('total_quota_bytes',models .BigIntegerField (default =5368709120 )),
    ('used_bytes',models .BigIntegerField (default =0 )),
    ('last_updated',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Квота хранилища пользователя',
    'verbose_name_plural':'Квоты хранилища пользователей',
    },
    ),
    migrations .RemoveField (
    model_name ='file',
    name ='course',
    ),
    migrations .AlterField (
    model_name ='fileactivity',
    name ='activity_type',
    field =models .CharField (choices =[('upload','Uploaded'),('download','Downloaded'),('view','Viewed'),('edit','Edited'),('delete','Deleted'),('share','Shared'),('comment','Commented'),('version_create','Created new version'),('favorite_add','Added to favorites'),('favorite_remove','Removed from favorites')],max_length =20 ),
    ),
    migrations .AddIndex (
    model_name ='fileactivity',
    index =models .Index (fields =['user','-created_at'],name ='file_manage_user_id_f66d31_idx'),
    ),
    migrations .AddIndex (
    model_name ='fileactivity',
    index =models .Index (fields =['activity_type','-created_at'],name ='file_manage_activit_736b0d_idx'),
    ),
    migrations .AddField (
    model_name ='file',
    name ='category',
    field =models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='files',to ='file_manager.filecategory'),
    ),
    migrations .AddField (
    model_name ='file',
    name ='tags',
    field =models .ManyToManyField (blank =True ,related_name ='files',to ='file_manager.tag'),
    ),
    migrations .AddIndex (
    model_name ='file',
    index =models .Index (fields =['extracted_text'],name ='file_manage_extract_20066c_idx'),
    ),
    migrations .AddField (
    model_name ='userstoragequota',
    name ='user',
    field =models .OneToOneField (on_delete =django .db .models .deletion .CASCADE ,related_name ='storage_quota',to =settings .AUTH_USER_MODEL ),
    ),
    ]
