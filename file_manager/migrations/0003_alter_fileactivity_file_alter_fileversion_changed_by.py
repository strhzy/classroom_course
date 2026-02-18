

import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    dependencies =[
    ('file_manager','0002_filecategory_tag_userstoragequota_remove_file_course_and_more'),
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .AlterField (
    model_name ='fileactivity',
    name ='file',
    field =models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='activities',to ='file_manager.file'),
    ),
    migrations .AlterField (
    model_name ='fileversion',
    name ='changed_by',
    field =models .ForeignKey (null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='file_versions',to =settings .AUTH_USER_MODEL ),
    ),
    ]
