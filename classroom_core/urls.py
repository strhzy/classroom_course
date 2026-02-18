from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'classroom_core'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='classroom_core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='classroom_core:login'), name='logout'),
    
    path('', views.course_list, name='course_list'),
    path('create/', views.course_create, name='course_create'),
    path('<int:course_id>/', views.course_detail, name='course_detail'),
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
    path('submissions/<int:submission_id>/grade/', views.assignment_grade, name='assignment_grade'),
    
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('<int:course_id>/announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:announcement_id>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', views.announcement_delete, name='announcement_delete'),
    
    path('<int:course_id>/students/', views.student_list, name='student_list'),
    path('<int:course_id>/students/enroll/', views.student_enroll, name='student_enroll'),
    path('<int:course_id>/students/<int:student_id>/remove/', views.student_remove, name='student_remove'),
    
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/add-students/', views.group_add_students, name='group_add_students'),
    
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_view_user'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]