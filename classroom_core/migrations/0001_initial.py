

import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    initial =True 

    dependencies =[
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .CreateModel (
    name ='Assignment',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('description',models .TextField ()),
    ('status',models .CharField (choices =[('draft','Черновик'),('published','Опубликовано'),('closed','Закрыто')],default ='draft',max_length =20 )),
    ('due_date',models .DateTimeField (blank =True ,null =True )),
    ('allow_late_submissions',models .BooleanField (default =False )),
    ('max_points',models .IntegerField (default =100 )),
    ('passing_score',models .IntegerField (default =50 )),
    ('is_group_assignment',models .BooleanField (default =False )),
    ('group_size_min',models .IntegerField (default =1 )),
    ('group_size_max',models .IntegerField (default =1 )),
    ('attachment',models .FileField (blank =True ,null =True ,upload_to ='assignment_attachments/')),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('published_at',models .DateTimeField (blank =True ,null =True )),
    ],
    options ={
    'verbose_name':'Задание',
    'verbose_name_plural':'Задания',
    'ordering':['-due_date','-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='AssignmentSubmission',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('text_response',models .TextField (blank =True )),
    ('file_submission',models .FileField (blank =True ,null =True ,upload_to ='assignment_submissions/')),
    ('status',models .CharField (choices =[('submitted','Отправлено'),('graded','Оценено'),('returned','Возвращено на доработку')],default ='submitted',max_length =20 )),
    ('score',models .IntegerField (blank =True ,null =True )),
    ('feedback',models .TextField (blank =True )),
    ('graded_at',models .DateTimeField (blank =True ,null =True )),
    ('submitted_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Решение задания',
    'verbose_name_plural':'Решения заданий',
    'ordering':['-submitted_at'],
    },
    ),
    migrations .CreateModel (
    name ='Course',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('description',models .TextField ()),
    ('short_description',models .CharField (blank =True ,max_length =200 )),
    ('status',models .CharField (choices =[('draft','Черновик'),('active','Активный'),('archived','Архивирован'),('completed','Завершен')],default ='draft',max_length =20 )),
    ('start_date',models .DateTimeField (blank =True ,null =True )),
    ('end_date',models .DateTimeField (blank =True ,null =True )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('cover_image',models .ImageField (blank =True ,null =True ,upload_to ='course_covers/')),
    ('color',models .CharField (default ='#3498db',max_length =7 )),
    ('code',models .CharField (blank =True ,max_length =20 ,unique =True )),
    ('is_public',models .BooleanField (default =False )),
    ('allow_self_enrollment',models .BooleanField (default =True )),
    ('max_students',models .IntegerField (blank =True ,null =True )),
    ],
    options ={
    'verbose_name':'Курс',
    'verbose_name_plural':'Курсы',
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='CourseDiscussion',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('content',models .TextField ()),
    ('is_pinned',models .BooleanField (default =False )),
    ('is_locked',models .BooleanField (default =False )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Обсуждение',
    'verbose_name_plural':'Обсуждения',
    'ordering':['-is_pinned','-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='CourseGrade',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('grade',models .DecimalField (blank =True ,decimal_places =2 ,max_digits =5 ,null =True )),
    ('letter_grade',models .CharField (blank =True ,max_length =2 )),
    ('completion_percentage',models .IntegerField (default =0 )),
    ('comments',models .TextField (blank =True )),
    ('is_passing',models .BooleanField (default =False )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Оценка курса',
    'verbose_name_plural':'Оценки курса',
    },
    ),
    migrations .CreateModel (
    name ='CourseMaterial',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('description',models .TextField (blank =True )),
    ('material_type',models .CharField (choices =[('file','Файл'),('link','Ссылка'),('video','Видео'),('text','Текст'),('assignment','Задание')],max_length =20 )),
    ('file',models .FileField (blank =True ,null =True ,upload_to ='course_materials/')),
    ('url',models .URLField (blank =True )),
    ('content',models .TextField (blank =True )),
    ('order',models .IntegerField (default =0 )),
    ('is_visible',models .BooleanField (default =True )),
    ('is_required',models .BooleanField (default =False )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Учебный материал',
    'verbose_name_plural':'Учебные материалы',
    'ordering':['section','order'],
    },
    ),
    migrations .CreateModel (
    name ='CourseNotification',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('message',models .TextField ()),
    ('notification_type',models .CharField (choices =[('announcement','Объявление'),('assignment','Задание'),('grade','Оценка'),('general','Общее')],max_length =20 )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ],
    options ={
    'verbose_name':'Уведомление курса',
    'verbose_name_plural':'Уведомления курса',
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='CourseSection',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('description',models .TextField (blank =True )),
    ('order',models .IntegerField (default =0 )),
    ('is_visible',models .BooleanField (default =True )),
    ],
    options ={
    'verbose_name':'Раздел курса',
    'verbose_name_plural':'Разделы курса',
    'ordering':['course','order'],
    },
    ),
    migrations .CreateModel (
    name ='DiscussionReply',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('content',models .TextField ()),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ],
    options ={
    'verbose_name':'Ответ на обсуждение',
    'verbose_name_plural':'Ответы на обсуждения',
    'ordering':['created_at'],
    },
    ),
    migrations .CreateModel (
    name ='Announcement',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =255 )),
    ('content',models .TextField ()),
    ('is_pinned',models .BooleanField (default =False )),
    ('send_email_notification',models .BooleanField (default =False )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('published_at',models .DateTimeField (blank =True ,null =True )),
    ('author',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='announcements',to =settings .AUTH_USER_MODEL )),
    ],
    options ={
    'verbose_name':'Объявление',
    'verbose_name_plural':'Объявления',
    'ordering':['-is_pinned','-created_at'],
    },
    ),
    ]
