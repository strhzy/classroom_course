from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .core_admin import views as core_admin_views

app_name = 'classroom_core'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='classroom_core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='classroom_core:login'), name='logout'),
    path(
        'password-reset/',
        views.PasswordResetRequestView.as_view(),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='classroom_core/password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='classroom_core/password_reset_confirm.html',
            success_url=reverse_lazy('classroom_core:password_reset_complete'),
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='classroom_core/password_reset_complete.html'),
        name='password_reset_complete'
    ),
    
    path('', views.course_list, name='course_list'),
    path('create/', views.course_create, name='course_create'),
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/teaching-assistants/manage/', views.course_manage_teaching_assistants, name='course_manage_teaching_assistants'),
    path('<int:course_id>/edit/', views.course_edit, name='course_edit'),
    path('<int:course_id>/delete/', views.course_delete, name='course_delete'),
    
    path('<int:course_id>/sections/create/', views.section_create, name='section_create'),
    path('sections/<int:section_id>/edit/', views.section_edit, name='section_edit'),
    path('sections/<int:section_id>/delete/', views.section_delete, name='section_delete'),
    
    path('sections/<int:section_id>/materials/create/', views.material_create, name='material_create'),
    path('materials/<int:material_id>/edit/', views.material_edit, name='material_edit'),
    path('materials/<int:material_id>/delete/', views.material_delete, name='material_delete'),
    
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('<int:course_id>/assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:assignment_id>/edit/', views.assignment_edit, name='assignment_edit'),
    path('assignments/<int:assignment_id>/delete/', views.assignment_delete, name='assignment_delete'),
    path('assignments/<int:assignment_id>/submit/', views.assignment_submit, name='assignment_submit'),
    path('assignments/<int:assignment_id>/quiz-submit/', views.assignment_quiz_submit, name='assignment_quiz_submit'),
    path('submissions/<int:submission_id>/grade/', views.assignment_grade, name='assignment_grade'),
    
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('<int:course_id>/announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:announcement_id>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', views.announcement_delete, name='announcement_delete'),
    
    path('<int:course_id>/students/', views.student_list, name='student_list'),
    path('<int:course_id>/students/enroll/', views.student_enroll, name='student_enroll'),
    path('<int:course_id>/students/<int:student_id>/remove/', views.student_remove, name='student_remove'),
    path('<int:course_id>/submissions/', views.course_submissions, name='course_submissions'),
    path('<int:course_id>/gradebook/', views.course_gradebook, name='course_gradebook'),
    path('<int:course_id>/gradebook/lessons/add/', views.course_gradebook_add_lesson, name='course_gradebook_add_lesson'),
    path('<int:course_id>/gradebook/lessons/<int:lesson_id>/topic/', views.course_gradebook_update_topic, name='course_gradebook_update_topic'),
    path('<int:course_id>/gradebook/update/', views.course_gradebook_update, name='course_gradebook_update'),
    path('<int:course_id>/gradebook/export/', views.course_gradebook_export, name='course_gradebook_export'),
    path('<int:course_id>/gradebook/import/', views.course_gradebook_import, name='course_gradebook_import'),
    path('<int:course_id>/gradebook/columns/create/', views.course_gradebook_column_create, name='course_gradebook_column_create'),
    
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/add-students/', views.group_add_students, name='group_add_students'),

                              
    path('courses-for-enrollment/', views.for_enrollment_course_list, name='for_enrollment_course_list'),
    path('enrollment-request/<int:course_id>/', views.course_enrollment_request_create, name='course_enrollment_request_create'),
    path('<int:course_id>/enrollment-requests/', views.course_enrollment_request_list, name='course_enrollment_request_list'),
    path('enrollment-requests/<int:request_id>/', views.course_enrollment_request_detail, name='course_enrollment_request_detail'),
    path('enrollment-requests/<int:request_id>/review/', views.course_enrollment_request_review, name='course_enrollment_request_review'),

                   
    path('assignments/<int:assignment_id>/files/create/', views.assignment_file_create, name='assignment_file_create'),
    path('assignments/<int:assignment_id>/files/', views.assignment_file_list, name='assignment_file_list'),
    path('assignments/files/<int:file_id>/delete/', views.assignment_file_delete, name='assignment_file_delete'),

                             
    path('assignments/files/<int:file_id>/review/create/', views.assignment_file_review_create, name='assignment_file_review_create'),
    path('assignments/files/reviews/<int:review_id>/', views.assignment_file_review_detail, name='assignment_file_review_detail'),
    path('assignments/files/reviews/<int:review_id>/edit/', views.assignment_file_review_edit, name='assignment_file_review_edit'),

    path('profile/', views.profile_view, name='profile_view'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_view_user'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('management/dashboard/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('management/courses/', views.custom_admin_courses, name='custom_admin_courses'),
    path('management/courses/create/', views.custom_admin_course_create, name='custom_admin_course_create'),
    path('management/courses/<int:course_id>/edit/', views.custom_admin_course_edit, name='custom_admin_course_edit'),
    path('management/courses/<int:course_id>/delete/', views.custom_admin_course_delete, name='custom_admin_course_delete'),
    path('management/assignments/', views.custom_admin_assignments, name='custom_admin_assignments'),
    path('management/assignments/create/', views.custom_admin_assignment_create, name='custom_admin_assignment_create'),
    path('management/assignments/<int:assignment_id>/edit/', views.custom_admin_assignment_edit, name='custom_admin_assignment_edit'),
    path('management/assignments/<int:assignment_id>/delete/', views.custom_admin_assignment_delete, name='custom_admin_assignment_delete'),
    path('management/students/', views.custom_admin_students, name='custom_admin_students'),
    path('management/students/create/', views.custom_admin_student_create, name='custom_admin_student_create'),
    path('management/students/<int:user_id>/edit/', views.custom_admin_student_edit, name='custom_admin_student_edit'),
    path('management/students/<int:user_id>/delete/', views.custom_admin_student_delete, name='custom_admin_student_delete'),

    path('management/core-admin/', core_admin_views.core_admin_index, name='core_admin_index'),
    path(
        'management/core-admin/backup/postgres/',
        core_admin_views.core_admin_backup_postgres_download,
        name='core_admin_backup_postgres',
    ),
    path(
        'management/core-admin/backup/postgres/restore/',
        core_admin_views.core_admin_backup_postgres_restore,
        name='core_admin_backup_postgres_restore',
    ),
    path('management/core-admin/<str:model_name>/', core_admin_views.core_admin_changelist, name='core_admin_changelist'),
    path('management/core-admin/<str:model_name>/add/', core_admin_views.core_admin_add, name='core_admin_add'),
    path(
        'management/core-admin/<str:model_name>/<int:object_id>/change/',
        core_admin_views.core_admin_change,
        name='core_admin_change',
    ),
    path(
        'management/core-admin/<str:model_name>/<int:object_id>/delete/',
        core_admin_views.core_admin_delete,
        name='core_admin_delete',
    ),
    path(
        'management/core-admin/<str:model_name>/bulk-delete/',
        core_admin_views.core_admin_bulk_delete,
        name='core_admin_bulk_delete',
    ),
]