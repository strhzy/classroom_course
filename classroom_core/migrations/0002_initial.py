

import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    initial =True 

    dependencies =[
    ('classroom_core','0001_initial'),
    ('file_manager','0001_initial'),
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .AddField (
    model_name ='announcement',
    name ='files',
    field =models .ManyToManyField (blank =True ,related_name ='announcements',to ='file_manager.file'),
    ),
    migrations .AddField (
    model_name ='assignment',
    name ='files',
    field =models .ManyToManyField (blank =True ,related_name ='assignments',to ='file_manager.file'),
    ),
    migrations .AddField (
    model_name ='assignmentsubmission',
    name ='assignment',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='submissions',to ='classroom_core.assignment'),
    ),
    migrations .AddField (
    model_name ='assignmentsubmission',
    name ='graded_by',
    field =models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='graded_submissions',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='assignmentsubmission',
    name ='group_members',
    field =models .ManyToManyField (blank =True ,related_name ='group_submissions',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='assignmentsubmission',
    name ='student',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='assignment_submissions',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='course',
    name ='instructor',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='courses_created',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='course',
    name ='students',
    field =models .ManyToManyField (blank =True ,related_name ='courses_enrolled',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='course',
    name ='teaching_assistants',
    field =models .ManyToManyField (blank =True ,related_name ='courses_assisting',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='assignment',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='assignments',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='announcement',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='announcements',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='coursediscussion',
    name ='author',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='course_discussions',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='coursediscussion',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='discussions',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='coursegrade',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='grades',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='coursegrade',
    name ='student',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='course_grades',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='coursematerial',
    name ='files',
    field =models .ManyToManyField (blank =True ,related_name ='course_materials',to ='file_manager.file'),
    ),
    migrations .AddField (
    model_name ='coursenotification',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='notifications',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='coursenotification',
    name ='is_read',
    field =models .ManyToManyField (blank =True ,related_name ='read_notifications',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='coursenotification',
    name ='recipients',
    field =models .ManyToManyField (related_name ='course_notifications',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='coursesection',
    name ='course',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='sections',to ='classroom_core.course'),
    ),
    migrations .AddField (
    model_name ='coursematerial',
    name ='section',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='materials',to ='classroom_core.coursesection'),
    ),
    migrations .AddField (
    model_name ='assignment',
    name ='section',
    field =models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='assignments',to ='classroom_core.coursesection'),
    ),
    migrations .AddField (
    model_name ='discussionreply',
    name ='author',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='discussion_replies',to =settings .AUTH_USER_MODEL ),
    ),
    migrations .AddField (
    model_name ='discussionreply',
    name ='discussion',
    field =models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='replies',to ='classroom_core.coursediscussion'),
    ),
    migrations .AddField (
    model_name ='discussionreply',
    name ='parent',
    field =models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .CASCADE ,related_name ='replies',to ='classroom_core.discussionreply'),
    ),
    migrations .AlterUniqueTogether (
    name ='assignmentsubmission',
    unique_together ={('assignment','student')},
    ),
    migrations .AddIndex (
    model_name ='course',
    index =models .Index (fields =['status','-created_at'],name ='classroom_c_status_b121b6_idx'),
    ),
    migrations .AddIndex (
    model_name ='course',
    index =models .Index (fields =['code'],name ='classroom_c_code_62ebea_idx'),
    ),
    migrations .AlterUniqueTogether (
    name ='coursegrade',
    unique_together ={('course','student')},
    ),
    ]
