from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Course, CourseSection, CourseMaterial, Assignment, 
    AssignmentSubmission, Announcement, CourseDiscussion, 
    DiscussionReply, CourseGrade, CourseNotification
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'instructor', 'status_badge', 
        'student_count', 'progress_display', 'created_at'
    ]
    list_filter = [
        'status', 'is_public', 'allow_self_enrollment', 
        'created_at', 'instructor'
    ]
    search_fields = [
        'title', 'description', 'code', 'instructor__username'
    ]
    filter_horizontal = ['teaching_assistants', 'students']
    readonly_fields = ['code', 'created_at', 'updated_at', 'progress_display']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'short_description', 'code')
        }),
        ('Преподаватели и студенты', {
            'fields': ('instructor', 'teaching_assistants', 'students')
        }),
        ('Настройки курса', {
            'fields': ('status', 'is_public', 'allow_self_enrollment', 'max_students')
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date', 'created_at', 'updated_at')
        }),
        ('Медиа', {
            'fields': ('cover_image', 'color')
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'active': 'success',
            'archived': 'warning',
            'completed': 'info',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def student_count(self, obj):
        count = obj.get_student_count()
        url = reverse('admin:classroom_core_course_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, count)
    student_count.short_description = 'Студентов'
    
    def progress_display(self, obj):
        progress = obj.get_progress()
        return format_html(
            '<div class="progress" style="width: 100px; height: 20px;">'
            '<div class="progress-bar bg-primary" role="progressbar" '
            'style="width: {}%;" aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
            '{}%</div></div>',
            progress, progress, progress
        )
    progress_display.short_description = 'Прогресс'

@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = [
        'course', 'title', 'order', 'is_visible', 
        'material_count'
    ]
    list_filter = ['course', 'is_visible', 'order']
    search_fields = ['title', 'description', 'course__title']
    list_editable = ['order', 'is_visible']
    
    def material_count(self, obj):
        return obj.materials.count()
    material_count.short_description = 'Материалов'

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = [
        'section', 'title', 'material_type_badge', 
        'order', 'is_visible', 'is_required'
    ]
    list_filter = [
        'material_type', 'section__course', 
        'is_visible', 'is_required', 'order'
    ]
    search_fields = ['title', 'description', 'section__title']
    list_editable = ['order', 'is_visible', 'is_required']
    
    def material_type_badge(self, obj):
        icons = {
            'file': '📄',
            'link': '🔗',
            'video': '🎬',
            'text': '📝',
            'assignment': '📝',
        }
        icon = icons.get(obj.material_type, '📎')
        return format_html('{} {}', icon, obj.get_material_type_display())
    material_type_badge.short_description = 'Тип материала'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'due_date', 'max_points', 
        'status_badge', 'submission_count'
    ]
    list_filter = [
        'status', 'course', 'due_date', 'is_group_assignment'
    ]
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['published_at']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('course', 'section', 'title', 'description')
        }),
        ('Статус и публикация', {
            'fields': ('status', 'published_at')
        }),
        ('Сроки и баллы', {
            'fields': ('due_date', 'allow_late_submissions', 'max_points', 'passing_score')
        }),
        ('Групповая работа', {
            'fields': ('is_group_assignment', 'group_size_min', 'group_size_max'),
            'classes': ('collapse',)
        }),
        ('Прикрепленные файлы', {
            'fields': ('attachment',),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'published': 'success',
            'closed': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def submission_count(self, obj):
        count = obj.submissions.count()
        url = reverse('admin:classroom_core_assignmentsubmission_changelist')
        return format_html('<a href="{}?assignment__id={}"><strong>{}</strong></a>', url, obj.id, count)
    submission_count.short_description = 'Решений'

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'assignment', 'student', 'status_badge', 
        'score_display', 'submitted_at', 'is_late_badge'
    ]
    list_filter = [
        'status', 'assignment__course', 'submitted_at', 
        'graded_at', 'assignment'
    ]
    search_fields = [
        'student__username', 'assignment__title', 
        'feedback', 'text_response'
    ]
    readonly_fields = ['submitted_at', 'updated_at', 'graded_at']
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('assignment', 'student', 'group_members')
        }),
        ('Решение', {
            'fields': ('text_response', 'file_submission')
        }),
        ('Оценка', {
            'fields': ('status', 'score', 'feedback', 'graded_by', 'graded_at')
        }),
        ('Временные метки', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'submitted': 'primary',
            'graded': 'success',
            'returned': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def score_display(self, obj):
        if obj.score is not None:
            if obj.score >= obj.assignment.passing_score:
                return format_html('<span class="text-success"><strong>{}</strong></span>', obj.score)
            else:
                return format_html('<span class="text-danger"><strong>{}</strong></span>', obj.score)
        return '—'
    score_display.short_description = 'Баллы'
    
    def is_late_badge(self, obj):
        if obj.is_late():
            return format_html('<span class="badge bg-danger">Опоздание</span>')
        return '—'
    is_late_badge.short_description = 'Опоздание'

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'author', 'is_pinned', 
        'created_at', 'published_at'
    ]
    list_filter = [
        'course', 'is_pinned', 'created_at', 'author'
    ]
    search_fields = ['title', 'content', 'course__title', 'author__username']
    readonly_fields = ['published_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('course', 'title', 'content', 'author')
        }),
        ('Настройки', {
            'fields': ('is_pinned', 'send_email_notification')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(CourseDiscussion)
class CourseDiscussionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'author', 'is_pinned', 
        'is_locked', 'reply_count', 'created_at'
    ]
    list_filter = [
        'course', 'is_pinned', 'is_locked', 
        'created_at', 'author'
    ]
    search_fields = ['title', 'content', 'course__title', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def reply_count(self, obj):
        count = obj.get_reply_count()
        return count
    reply_count.short_description = 'Ответов'

@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = [
        'discussion', 'author', 'content_preview', 
        'parent_reply', 'created_at'
    ]
    list_filter = ['discussion__course', 'created_at', 'author']
    search_fields = ['content', 'discussion__title', 'author__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Контент'
    
    def parent_reply(self, obj):
        return obj.parent.content[:30] + '...' if obj.parent else '—'
    parent_reply.short_description = 'Родительский ответ'

@admin.register(CourseGrade)
class CourseGradeAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'course', 'grade_display', 
        'letter_grade', 'completion_percentage', 'is_passing'
    ]
    list_filter = [
        'course', 'is_passing', 'letter_grade', 
        'completion_percentage'
    ]
    search_fields = [
        'student__username', 'course__title', 'comments'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('course', 'student')
        }),
        ('Оценки', {
            'fields': ('grade', 'letter_grade', 'is_passing')
        }),
        ('Прогресс', {
            'fields': ('completion_percentage', 'comments')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def grade_display(self, obj):
        if obj.grade is not None:
            grade_value = float(obj.grade)
            if grade_value >= 90:
                color = 'success'
            elif grade_value >= 70:
                color = 'warning'
            else:
                color = 'danger'
            return format_html('<span class="badge bg-{}">{}</span>', color, obj.grade)
        return '—'
    grade_display.short_description = 'Оценка'

@admin.register(CourseNotification)
class CourseNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'notification_type_badge', 
        'recipient_count', 'created_at'
    ]
    list_filter = [
        'course', 'notification_type', 'created_at'
    ]
    search_fields = ['title', 'message', 'course__title']
    filter_horizontal = ['recipients', 'is_read']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def notification_type_badge(self, obj):
        colors = {
            'announcement': 'info',
            'assignment': 'warning',
            'grade': 'success',
            'general': 'secondary',
        }
        color = colors.get(obj.notification_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Тип уведомления'
    
    def recipient_count(self, obj):
        return obj.recipients.count()
    recipient_count.short_description = 'Получателей'