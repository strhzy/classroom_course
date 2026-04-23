from django.contrib import admin 
from django.utils.html import format_html 
from . models import(
File ,FileCategory ,Tag ,FileComment ,
FileVersion ,FileActivity ,UserStorageQuota 
)

@admin.register(FileCategory )
class FileCategoryAdmin(admin.ModelAdmin ):
    list_display =['name','icon','order','get_file_count']
    list_editable =['order']
    list_filter =['order']
    search_fields =['name','description']

    def get_file_count(self ,obj ):
        return obj.files.count()
    get_file_count.short_description ='Количество файлов'

@admin.register(Tag )
class TagAdmin(admin.ModelAdmin ):
    list_display =['name','color_display','get_file_count']
    search_fields =['name']

    def color_display(self ,obj ):
        return format_html(
        '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%;"></div>',
        obj.color 
        )
    color_display.short_description ='Цвет'

    def get_file_count(self ,obj ):
        return obj.files.count()
    get_file_count.short_description ='Количество файлов'

@admin.register(File )
class FileAdmin(admin.ModelAdmin ):
    list_display =[
    'title_display','file_type','uploaded_by',
    'uploaded_at','file_size_display','visibility',
    'version','download_count'
    ]
    list_filter =[
    'file_type','visibility','uploaded_at',
    'category','tags','is_folder'
    ]
    search_fields =[
    'title','description','extracted_text',
    'uploaded_by__username','uploaded_by__email'
    ]
    readonly_fields =[
    'file_size','extracted_text','download_count',
    'version','uploaded_at','updated_at'
    ]
    filter_horizontal =['tags','shared_with','favorite']
    date_hierarchy ='uploaded_at'

    def title_display(self ,obj ):
        if obj.is_folder :
            return format_html('<i class="bi bi-folder2"></i> {}',obj.title )
        else :
            return format_html('<i class="bi bi-file-earmark"></i> {}',obj.title )
    title_display.short_description ='Название'

    def file_size_display(self ,obj ):
        return obj.get_file_size_display()
    file_size_display.short_description ='Размер'

@admin.register(FileComment )
class FileCommentAdmin(admin.ModelAdmin ):
    list_display =[
    'file','author','created_at','content_preview',
    'parent_comment'
    ]
    list_filter =['created_at','author']
    search_fields =['content','file__title','author__username']
    readonly_fields =['created_at','updated_at']

    def content_preview(self ,obj ):
        return obj.content [:50 ]+'...'if len(obj.content )>50 else obj.content 
    content_preview.short_description ='Контент'

    def parent_comment(self ,obj ):
        return obj.parent.content [:30 ]+'...'if obj.parent else '—'
    parent_comment.short_description ='Родительский комментарий'

@admin.register(FileVersion )
class FileVersionAdmin(admin.ModelAdmin ):
    list_display =[
    'file','version_number','changed_by',
    'created_at','change_description_preview'
    ]
    list_filter =['created_at','changed_by']
    search_fields =[
    'file__title','change_description',
    'changed_by__username'
    ]
    readonly_fields =['created_at']

    def change_description_preview(self ,obj ):
        return obj.change_description [:50 ]+'...'if len(obj.change_description )>50 else obj.change_description 
    change_description_preview.short_description ='Описание изменений'

@admin.register(FileActivity )
class FileActivityAdmin(admin.ModelAdmin ):
    list_display =[
    'user','activity_type_display','file',
    'created_at','ip_address'
    ]
    list_filter =[
    'activity_type','created_at','user','ip_address'
    ]
    search_fields =[
    'user__username','file__title','description'
    ]
    readonly_fields =['created_at']
    date_hierarchy ='created_at'

    def activity_type_display(self ,obj ):
        colors ={
        'upload':'success',
        'download':'primary',
        'view':'info',
        'edit':'warning',
        'delete':'danger',
        'share':'secondary',
        'comment':'dark',
        'version_create':'purple',
        'favorite_add':'pink',
        'favorite_remove':'pink',
        }
        color =colors.get(obj.activity_type ,'secondary')
        return format_html(
        '<span class="badge bg-{}">{}</span>',
        color ,obj.get_activity_type_display()
        )
    activity_type_display.short_description ='Тип активности'

@admin.register(UserStorageQuota )
class UserStorageQuotaAdmin(admin.ModelAdmin ):
    list_display =[
    'user','quota_display','used_percentage_display',
    'last_updated'
    ]
    list_filter =['last_updated']
    search_fields =['user__username','user__email']
    readonly_fields =['last_updated','used_bytes']

    def quota_display(self ,obj ):
        return obj.get_quota_display()
    quota_display.short_description ='Квота'

    def used_percentage_display(self ,obj ):

        percentage =obj.get_used_percentage()


        if not isinstance(percentage ,(int ,float )):
            try :
                percentage =float(percentage )
            except(ValueError ,TypeError ):
                percentage =0.0 


        percentage_str =f"{percentage :.1f}"
        width_str =f"{percentage :.1f}"

        color ='success'if percentage <80 else 'warning'if percentage <95 else 'danger'
        return format_html(
        '<div class="progress" style="width: 100px; height: 20px;">'
        '<div class="progress-bar bg-{}" role="progressbar" '
        'style="width: {}%;" aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
        '{}%</div></div>',
        color ,width_str ,percentage_str ,percentage_str 
        )
    used_percentage_display.short_description ='Использовано'