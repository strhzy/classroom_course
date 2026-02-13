from django.contrib import admin
from .models import (
    Course, CourseSection, CourseMaterial, 
    Assignment, AssignmentSubmission,
    Announcement, CourseDiscussion, DiscussionReply,
    CourseGrade, CourseNotification
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'status', 'get_student_count', 'created_at']
    list_filter = ['status', 'is_public', 'created_at']
    search_fields = ['title', 'description', 'code']
    filter_horizontal = ['teaching_assistants', 'students']
    readonly_fields = ['code', 'created_at', 'updated_at']
    
    def get_student_count(self, obj):
        return obj.get_student_count()
    get_student_count.short_description = 'Студентов'

@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_visible']
    list_filter = ['course', 'is_visible']
    search_fields = ['title', 'description']

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'material_type', 'order', 'is_visible']
    list_filter = ['material_type', 'section__course', 'is_visible']
    search_fields = ['title', 'description']
    filter_horizontal = ['files']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'due_date', 'max_points', 'status']
    list_filter = ['status', 'course', 'due_date']
    search_fields = ['title', 'description']
    readonly_fields = ['published_at']
    filter_horizontal = ['files']

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'status', 'score', 'submitted_at']
    list_filter = ['status', 'assignment__course', 'submitted_at']
    search_fields = ['student__username', 'assignment__title']
    readonly_fields = ['submitted_at', 'updated_at']

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'author', 'is_pinned', 'created_at']
    list_filter = ['course', 'is_pinned', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['published_at']
    filter_horizontal = ['files']

@admin.register(CourseDiscussion)
class CourseDiscussionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'author', 'get_reply_count', 'created_at']
    list_filter = ['course', 'is_pinned', 'created_at']
    search_fields = ['title', 'content']
    
    def get_reply_count(self, obj):
        return obj.get_reply_count()
    get_reply_count.short_description = 'Ответов'

@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ['discussion', 'author', 'created_at']
    list_filter = ['discussion__course', 'created_at']
    search_fields = ['content']

@admin.register(CourseGrade)
class CourseGradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'grade', 'letter_grade', 'is_passing']
    list_filter = ['course', 'is_passing', 'letter_grade']
    search_fields = ['student__username', 'course__title']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CourseNotification)
class CourseNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'notification_type', 'created_at']
    list_filter = ['course', 'notification_type', 'created_at']
    search_fields = ['title', 'message']