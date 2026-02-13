from django.contrib import admin
from .models import File, FileComment, FileVersion, FileActivity

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_type', 'uploaded_by', 'uploaded_at', 'get_file_size_display', 'visibility']
    list_filter = ['file_type', 'visibility', 'uploaded_at']
    search_fields = ['title', 'description', 'extracted_text']
    readonly_fields = ['file_size', 'extracted_text', 'download_count', 'version']
    filter_horizontal = ['shared_with', 'favorite']

@admin.register(FileComment)
class FileCommentAdmin(admin.ModelAdmin):
    list_display = ['file', 'author', 'created_at']
    list_filter = ['created_at']

@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = ['file', 'version_number', 'changed_by', 'created_at']
    list_filter = ['created_at']

@admin.register(FileActivity)
class FileActivityAdmin(admin.ModelAdmin):
    list_display = ['file', 'user', 'activity_type', 'created_at']
    list_filter = ['activity_type', 'created_at']