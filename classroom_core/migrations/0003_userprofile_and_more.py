

import django.core.validators 
import django.db.models.deletion 
from django.conf import settings 
from django.db import migrations ,models 


class Migration(migrations.Migration ):

    dependencies =[
   ('classroom_core','0002_initial'),
    migrations.swappable_dependency(settings.AUTH_USER_MODEL ),
    ]

    operations =[
    migrations.CreateModel(
    name ='UserProfile',
    fields =[
   ('id',models.BigAutoField(auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
   ('role',models.CharField(choices =[('student','Студент'),('teacher','Преподаватель'),('staff','Сотрудник учебной части'),('admin','Администратор')],default ='student',max_length =20 )),
   ('department',models.CharField(blank =True ,max_length =200 )),
   ('position',models.CharField(blank =True ,max_length =200 )),
   ('student_group',models.CharField(blank =True ,max_length =50 )),
   ('phone',models.CharField(blank =True ,max_length =20 )),
   ('avatar',models.ImageField(blank =True ,null =True ,upload_to ='avatars/')),
   ('created_at',models.DateTimeField(auto_now_add =True )),
   ('updated_at',models.DateTimeField(auto_now =True )),
    ],
    options ={
    'verbose_name':'Профиль пользователя',
    'verbose_name_plural':'Профили пользователей',
    },
    ),
    migrations.RemoveIndex(
    model_name ='course',
    name ='classroom_c_status_b121b6_idx',
    ),
    migrations.RemoveIndex(
    model_name ='course',
    name ='classroom_c_code_62ebea_idx',
    ),
    migrations.RemoveField(
    model_name ='announcement',
    name ='files',
    ),
    migrations.RemoveField(
    model_name ='assignment',
    name ='files',
    ),
    migrations.RemoveField(
    model_name ='coursematerial',
    name ='files',
    ),
    migrations.AlterField(
    model_name ='coursematerial',
    name ='file',
    field =models.FileField(blank =True ,null =True ,upload_to ='course_materials/',validators =[django.core.validators.FileExtensionValidator(allowed_extensions =['pdf','docx','xlsx','pptx','txt','zip','jpg','png','mp4','mp3'])]),
    ),
    migrations.AddField(
    model_name ='userprofile',
    name ='user',
    field =models.OneToOneField(on_delete =django.db.models.deletion.CASCADE ,related_name ='profile',to =settings.AUTH_USER_MODEL ),
    ),
    ]
