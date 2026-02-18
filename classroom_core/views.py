from django .shortcuts import render ,redirect ,get_object_or_404 
from django .contrib .auth .decorators import login_required 
from django .contrib import messages 
from django .core .exceptions import PermissionDenied 
from django .db .models import Q 
from django .core .paginator import Paginator 
from django .contrib .auth .models import User 
from .models import *
from .forms import *
from django .utils import timezone 

@login_required 
def course_list (request ):
    """Список курсов"""
    user_profile =request .user .profile 

    if user_profile .is_teacher ()or user_profile .is_staff ()or request .user .is_superuser :

        courses =Course .objects .all ()
    else :

        courses =Course .objects .filter (
        Q (instructor =request .user )|
        Q (teaching_assistants =request .user )|
        Q (students =request .user )
        ).distinct ()


    status =request .GET .get ('status')
    if status :
        courses =courses .filter (status =status )


    query =request .GET .get ('query')
    if query :
        courses =courses .filter (
        Q (title__icontains =query )|
        Q (description__icontains =query )|
        Q (code__icontains =query )
        )


    sort_by =request .GET .get ('sort','-created_at')
    courses =courses .order_by (sort_by )


    paginator =Paginator (courses ,12 )
    page_number =request .GET .get ('page')
    page_obj =paginator .get_page (page_number )

    context ={
    'page_obj':page_obj ,
    'status':status ,
    'query':query ,
    'sort_by':sort_by ,
    }

    return render (request ,'classroom_core/course_list.html',context )

@login_required 
def course_detail (request ,course_id ):
    """Детали курса"""
    course =get_object_or_404 (Course ,id =course_id )


    if not course .can_access (request .user ):
        raise PermissionDenied 


    announcements =course .announcements .all ().order_by ('-is_pinned','-created_at')[:5 ]
    sections =course .sections .all ().order_by ('order')
    assignments =course .assignments .filter (status ='published').order_by ('-due_date')
    students =course .students .all ()


    is_student =course .students .filter (id =request .user .id ).exists ()

    context ={
    'course':course ,
    'announcements':announcements ,
    'sections':sections ,
    'assignments':assignments ,
    'students':students ,
    'is_student':is_student ,
    }

    return render (request ,'classroom_core/course_detail.html',context )

@login_required 
def course_create (request ):
    """Создание нового курса"""
    user_profile =request .user .profile 


    if not (user_profile .is_teacher ()or user_profile .is_staff ()or request .user .is_superuser ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseForm (request .POST ,request .FILES )
        if form .is_valid ():
            course =form .save (commit =False )
            course .instructor =request .user 
            course .save ()
            messages .success (request ,'Курс успешно создан')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseForm ()

    return render (request ,'classroom_core/course_form.html',{
    'form':form ,
    'title':'Создать курс'
    })

@login_required 
def course_edit (request ,course_id ):
    """Редактирование курса"""
    course =get_object_or_404 (Course ,id =course_id )


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseForm (request .POST ,request .FILES ,instance =course )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Курс успешно обновлен')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseForm (instance =course )

    return render (request ,'classroom_core/course_form.html',{
    'form':form ,
    'title':'Редактировать курс',
    'course':course 
    })

@login_required 
def course_delete (request ,course_id ):
    """Удаление курса"""
    course =get_object_or_404 (Course ,id =course_id )


    if not course .can_delete (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        course .delete ()
        messages .success (request ,'Курс успешно удален')
        return redirect ('classroom_core:course_list')

    return render (request ,'classroom_core/course_confirm_delete.html',{
    'course':course 
    })



@login_required 
def section_create (request ,course_id ):
    """Создание раздела курса"""
    course =get_object_or_404 (Course ,id =course_id )


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseSectionForm (request .POST )
        if form .is_valid ():
            section =form .save (commit =False )
            section .course =course 
            section .save ()
            messages .success (request ,'Раздел успешно создан')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseSectionForm ()

    return render (request ,'classroom_core/section_form.html',{
    'form':form ,
    'course':course ,
    'title':'Создать раздел'
    })

@login_required 
def section_edit (request ,section_id ):
    """Редактирование раздела курса"""
    section =get_object_or_404 (CourseSection ,id =section_id )
    course =section .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseSectionForm (request .POST ,instance =section )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Раздел успешно обновлен')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseSectionForm (instance =section )

    return render (request ,'classroom_core/section_form.html',{
    'form':form ,
    'course':course ,
    'section':section ,
    'title':'Редактировать раздел'
    })

@login_required 
def section_delete (request ,section_id ):
    """Удаление раздела курса"""
    section =get_object_or_404 (CourseSection ,id =section_id )
    course =section .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        section .delete ()
        messages .success (request ,'Раздел успешно удален')
        return redirect ('classroom_core:course_detail',course_id =course .id )

    return render (request ,'classroom_core/section_confirm_delete.html',{
    'section':section ,
    'course':course 
    })



@login_required 
def material_create (request ,section_id ):
    """Создание учебного материала"""
    section =get_object_or_404 (CourseSection ,id =section_id )
    course =section .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseMaterialForm (request .POST ,request .FILES )
        if form .is_valid ():
            material =form .save (commit =False )
            material .section =section 
            material .save ()
            messages .success (request ,'Материал успешно создан')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseMaterialForm ()

    return render (request ,'classroom_core/material_form.html',{
    'form':form ,
    'section':section ,
    'course':course ,
    'title':'Создать материал'
    })

@login_required 
def material_edit (request ,material_id ):
    """Редактирование учебного материала"""
    material =get_object_or_404 (CourseMaterial ,id =material_id )
    section =material .section 
    course =section .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =CourseMaterialForm (request .POST ,request .FILES ,instance =material )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Материал успешно обновлен')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =CourseMaterialForm (instance =material )

    return render (request ,'classroom_core/material_form.html',{
    'form':form ,
    'section':section ,
    'course':course ,
    'material':material ,
    'title':'Редактировать материал'
    })

@login_required 
def material_delete (request ,material_id ):
    """Удаление учебного материала"""
    material =get_object_or_404 (CourseMaterial ,id =material_id )
    section =material .section 
    course =section .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        material .delete ()
        messages .success (request ,'Материал успешно удален')
        return redirect ('classroom_core:course_detail',course_id =course .id )

    return render (request ,'classroom_core/material_confirm_delete.html',{
    'material':material ,
    'section':section ,
    'course':course 
    })



@login_required 
def assignment_list (request ):
    """Список заданий"""
    user_profile =request.user.profile 

    if user_profile.is_teacher() or user_profile.is_staff() or request.user.is_superuser:

        assignments =Assignment.objects.all()
    else :

        assignments =Assignment.objects.filter (
        course__students =request.user ,
        status ='published'
        )


    course_id =request.GET.get('course_id')
    if course_id :
        assignments =assignments .filter (course_id =course_id )


    status =request.GET.get('status')
    if status:
        assignments=assignments .filter (status =status )


    sort_by =request.GET.get('sort','-due_date')
    assignments =assignments .order_by (sort_by )


    paginator =Paginator (assignments ,12 )
    page_number =request .GET .get ('page')
    page_obj =paginator .get_page (page_number )

    context ={
    'page_obj':page_obj ,
    'course_id':course_id ,
    'status':status ,
    'sort_by':sort_by ,
    }

    return render (request ,'classroom_core/assignment_list.html',context )

@login_required 
def assignment_detail (request ,assignment_id ):
    """Детали задания"""
    assignment =get_object_or_404 (Assignment ,id =assignment_id )
    course =assignment .course 


    if not course .can_access (request .user ):
        raise PermissionDenied 


    is_student =course .students .filter (id =request .user .id ).exists ()


    submission =None 
    if is_student :
        submission =AssignmentSubmission .objects .filter (
        assignment =assignment ,
        student =request .user 
        ).first ()

    context ={
    'assignment':assignment ,
    'course':course ,
    'is_student':is_student ,
    'submission':submission ,
    }

    return render (request ,'classroom_core/assignment_detail.html',context )

@login_required 
def assignment_create (request ,course_id ):
    """Создание задания"""
    course =get_object_or_404 (Course ,id =course_id )


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =AssignmentForm (request .POST ,request .FILES )
        if form .is_valid ():
            assignment =form .save (commit =False )
            assignment .course =course 
            assignment .save ()
            messages .success (request ,'Задание успешно создано')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =AssignmentForm ()

    return render (request ,'classroom_core/assignment_form.html',{
    'form':form ,
    'course':course ,
    'title':'Создать задание'
    })

@login_required 
def assignment_edit (request ,assignment_id ):
    """Редактирование задания"""
    assignment =get_object_or_404 (Assignment ,id =assignment_id )
    course =assignment .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =AssignmentForm (request .POST ,request .FILES ,instance =assignment )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Задание успешно обновлено')
            return redirect ('classroom_core:assignment_detail',assignment_id =assignment .id )
    else :
        form =AssignmentForm (instance =assignment )

    return render (request ,'classroom_core/assignment_form.html',{
    'form':form ,
    'course':course ,
    'assignment':assignment ,
    'title':'Редактировать задание'
    })

@login_required 
def assignment_delete (request ,assignment_id ):
    """Удаление задания"""
    assignment =get_object_or_404 (Assignment ,id =assignment_id )
    course =assignment .course 


    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        assignment .delete ()
        messages .success (request ,'Задание успешно удалено')
        return redirect ('classroom_core:course_detail',course_id =course .id )

    return render (request ,'classroom_core/assignment_confirm_delete.html',{
    'assignment':assignment ,
    'course':course 
    })

@login_required 
def assignment_submit (request ,assignment_id ):
    """Отправка решения задания"""
    assignment =get_object_or_404 (Assignment ,id =assignment_id )
    course =assignment .course 


    if not course .can_access (request .user ):
        raise PermissionDenied 


    if not course .students .filter (id =request .user .id ).exists ():
        raise PermissionDenied 


    if not assignment .can_submit ():
        messages .error (request ,'Отправка решений для этого задания невозможна')
        return redirect ('classroom_core:assignment_detail',assignment_id =assignment .id )


    existing_submission =AssignmentSubmission .objects .filter (
    assignment =assignment ,
    student =request .user 
    ).first ()

    if existing_submission and existing_submission .status !='returned':
        messages .error (request ,'Вы уже отправили решение этого задания')
        return redirect ('classroom_core:assignment_detail',assignment_id =assignment .id )

    if request .method =='POST':
        form =AssignmentSubmissionForm (request .POST ,request .FILES )
        if form .is_valid ():
            submission =form .save (commit =False )
            submission .assignment =assignment 
            submission .student =request .user 
            submission .save ()

            messages .success (request ,'Решение успешно отправлено')
            return redirect ('classroom_core:assignment_detail',assignment_id =assignment .id )
    else :
        form =AssignmentSubmissionForm ()

    return render (request ,'classroom_core/assignment_submit.html',{
    'form':form ,
    'assignment':assignment ,
    'course':course 
    })

@login_required 
def assignment_grade (request ,submission_id ):
    """Оценка решения задания"""
    submission =get_object_or_404 (AssignmentSubmission ,id =submission_id )
    assignment =submission .assignment 
    course =assignment .course 


    if not assignment .can_grade (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =AssignmentGradeForm (request .POST ,instance =submission )
        if form .is_valid ():
            submission =form .save (commit =False )
            submission .graded_by =request .user 
            submission .graded_at =timezone .now ()
            submission .save ()

            messages .success (request ,'Решение успешно оценено')
            return redirect ('classroom_core:assignment_detail',assignment_id =assignment .id )
    else :
        form =AssignmentGradeForm (instance =submission )

    return render (request ,'classroom_core/assignment_grade.html',{
    'form':form ,
    'submission':submission ,
    'assignment':assignment ,
    'course':course 
    })



@login_required 
def announcement_list (request ):
    """Список объявлений"""
    user_profile =request .user .profile 

    if user_profile .is_teacher ()or user_profile .is_staff ()or request .user .is_superuser :

        announcements =Announcement .objects .all ()
    else :

        announcements =Announcement .objects .filter (
        course__students =request .user 
        )


    course_id =request .GET .get ('course_id')
    if course_id :
        announcements =announcements .filter (course_id =course_id )


    sort_by =request .GET .get ('sort','-is_pinned')
    announcements =announcements .order_by (sort_by )

    paginator =Paginator (announcements ,12 )
    page_number =request .GET .get ('page')
    page_obj =paginator .get_page (page_number )

    context ={
    'page_obj':page_obj ,
    'course_id':course_id ,
    'sort_by':sort_by ,
    }

    return render (request ,'classroom_core/announcement_list.html',context )

@login_required 
def announcement_detail (request ,announcement_id ):
    announcement =get_object_or_404 (Announcement ,id =announcement_id )
    course =announcement .course 

    if not course .can_access (request .user ):
        raise PermissionDenied 

    return render (request ,'classroom_core/announcement_detail.html',{
    'announcement':announcement ,
    'course':course 
    })

@login_required 
def announcement_create (request ,course_id ):
    course =get_object_or_404 (Course ,id =course_id )

    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =AnnouncementForm (request .POST )
        if form .is_valid ():
            announcement =form .save (commit =False )
            announcement .course =course 
            announcement .author =request .user 
            announcement .save ()
            messages .success (request ,'Объявление успешно создано')
            return redirect ('classroom_core:course_detail',course_id =course .id )
    else :
        form =AnnouncementForm ()

    return render (request ,'classroom_core/announcement_form.html',{
    'form':form ,
    'course':course ,
    'title':'Создать объявление'
    })

@login_required 
def announcement_edit (request ,announcement_id ):
    announcement =get_object_or_404 (Announcement ,id =announcement_id )
    course =announcement .course 

    if not announcement .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =AnnouncementForm (request .POST ,instance =announcement )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Объявление успешно обновлено')
            return redirect ('classroom_core:announcement_detail',announcement_id =announcement .id )
    else :
        form =AnnouncementForm (instance =announcement )

    return render (request ,'classroom_core/announcement_form.html',{
    'form':form ,
    'course':course ,
    'announcement':announcement ,
    'title':'Редактировать объявление'
    })

@login_required 
def announcement_delete (request ,announcement_id ):
    announcement =get_object_or_404 (Announcement ,id =announcement_id )
    course =announcement .course 

    if not announcement .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        announcement .delete ()
        messages .success (request ,'Объявление успешно удалено')
        return redirect ('classroom_core:course_detail',course_id =course .id )

    return render (request ,'classroom_core/announcement_confirm_delete.html',{
    'announcement':announcement ,
    'course':course 
    })

@login_required 
def student_list (request ,course_id ):
    course =get_object_or_404 (Course ,id =course_id )

    if not course .can_edit (request .user ):
        raise PermissionDenied 

    students =course .students .all ()

    query =request .GET .get ('query')
    if query :
        students =students .filter (
        Q (username__icontains =query )|
        Q (first_name__icontains =query )|
        Q (last_name__icontains =query )|
        Q (email__icontains =query )
        )

    paginator =Paginator (students ,20 )
    page_number =request .GET .get ('page')
    page_obj =paginator .get_page (page_number )

    context ={
    'course':course ,
    'page_obj':page_obj ,
    'query':query ,
    }

    return render (request ,'classroom_core/student_list.html',context )

@login_required 
def student_enroll (request ,course_id ):
    course =get_object_or_404 (Course ,id =course_id )

    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        form =StudentEnrollmentForm (request .POST )
        if form .is_valid ():
            students =form .cleaned_data ['students']
            for student in students :
                success ,message =course .add_student (student )
                if not success :
                    messages .warning (request ,f'{student .username }: {message }')

            if students :
                messages .success (request ,'Студенты успешно зачислены на курс')
            return redirect ('classroom_core:student_list',course_id =course .id )
    else :
        form =StudentEnrollmentForm ()

    return render (request ,'classroom_core/student_enroll.html',{
    'form':form ,
    'course':course 
    })

@login_required 
def student_remove (request ,course_id ,student_id ):
    course =get_object_or_404 (Course ,id =course_id )
    student =get_object_or_404 (User ,id =student_id )

    if not course .can_edit (request .user ):
        raise PermissionDenied 

    if request .method =='POST':
        success ,message =course .remove_student (student )
        if success :
            messages .success (request ,'Студент успешно удален с курса')
        else :
            messages .error (request ,message )
        return redirect ('classroom_core:student_list',course_id =course .id )

    return render (request ,'classroom_core/student_confirm_remove.html',{
    'course':course ,
    'student':student 
    })


@login_required 
def profile_view (request ,user_id =None ):
    if user_id :
        user =get_object_or_404 (User ,id =user_id )
    else :
        user =request .user 

    return render (request ,'classroom_core/profile_view.html',{
    'profile_user':user 
    })

@login_required 
def profile_edit (request ):
    if request .method =='POST':
        form =UserProfileForm (request .POST ,request .FILES ,instance =request .user .profile )
        if form .is_valid ():
            form .save ()
            messages .success (request ,'Профиль успешно обновлен')
            return redirect ('classroom_core:profile_view')
    else :
        form =UserProfileForm (instance =request .user .profile )

    return render (request ,'classroom_core/profile_form.html',{
    'form':form ,
    'title':'Редактировать профиль'
    })

@login_required
def student_list(request, course_id):
    """Список студентов курса"""
    course = get_object_or_404(Course, id=course_id)
    
    # Проверка прав
    if not course.can_edit(request.user):
        raise PermissionDenied
    
    # Получаем всех студентов курса (индивидуальных + из групп)
    all_students = course.get_all_enrolled_students()
    
    # Поиск
    query = request.GET.get('query')
    if query:
        all_students = all_students.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Пагинация
    paginator = Paginator(list(all_students), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'course': course,
        'page_obj': page_obj,
        'query': query,
        'individual_students': course.students.all(),
        'group_students': course.student_groups.all(),
    }
    
    return render(request, 'classroom_core/student_list.html', context)

@login_required
def student_enroll(request, course_id):
    """Зачисление студентов и групп на курс"""
    course = get_object_or_404(Course, id=course_id)
    
    # Проверка прав
    if not course.can_edit(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        # Обработка индивидуальных студентов
        student_form = StudentEnrollmentForm(request.POST, prefix='students')
        # Обработка групп студентов
        group_form = StudentGroupEnrollmentForm(request.POST, prefix='groups')
        
        students_added = 0
        groups_added = 0
        
        if student_form.is_valid():
            students = student_form.cleaned_data['students']
            for student in students:
                success, message = course.add_student(student)
                if success:
                    students_added += 1
                else:
                    messages.warning(request, f'{student.username}: {message}')
        
        if group_form.is_valid():
            groups = group_form.cleaned_data['groups']
            for group in groups:
                success, message = course.add_student_group(group)
                if success:
                    groups_added += 1
                else:
                    messages.warning(request, f'{group.name}: {message}')
        
        if students_added > 0 or groups_added > 0:
            messages.success(request, f'Успешно зачислено: {students_added} студентов и {groups_added} групп')
            return redirect('classroom_core:student_list', course_id=course.id)
    
    else:
        student_form = StudentEnrollmentForm(prefix='students')
        group_form = StudentGroupEnrollmentForm(prefix='groups')
    
    context = {
        'course': course,
        'student_form': student_form,
        'group_form': group_form,
    }
    
    return render(request, 'classroom_core/student_enroll.html', context)

@login_required
def student_remove(request, course_id, student_id):
    """Удаление студента с курса"""
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(User, id=student_id)
    
    # Проверка прав
    if not course.can_edit(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        success, message = course.remove_student(student)
        if success:
            messages.success(request, 'Студент успешно удален с курса')
        else:
            messages.error(request, message)
        return redirect('classroom_core:student_list', course_id=course.id)
    
    return render(request, 'classroom_core/student_confirm_remove.html', {
        'course': course,
        'student': student
    })

@login_required
def group_list(request):
    """Список групп студентов"""
    if not (request.user.profile.is_teacher() or request.user.profile.is_staff() or request.user.is_superuser):
        raise PermissionDenied
    
    groups = StudentGroup.objects.all()
    
    # Поиск
    query = request.GET.get('query')
    if query:
        groups = groups.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Пагинация
    paginator = Paginator(groups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
    }
    
    return render(request, 'classroom_core/group_list.html', context)

@login_required
def group_create(request):
    """Создание группы студентов"""
    if not (request.user.profile.is_teacher() or request.user.profile.is_staff() or request.user.is_superuser):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = StudentGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            messages.success(request, 'Группа успешно создана')
            return redirect('classroom_core:group_list')
    else:
        form = StudentGroupForm()
    
    return render(request, 'classroom_core/group_form.html', {
        'form': form,
        'title': 'Создать группу'
    })

@login_required
def group_edit(request, group_id):
    """Редактирование группы студентов"""
    group = get_object_or_404(StudentGroup, id=group_id)
    
    if not (request.user == group.created_by or request.user.profile.is_staff() or request.user.is_superuser):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = StudentGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Группа успешно обновлена')
            return redirect('classroom_core:group_list')
    else:
        form = StudentGroupForm(instance=group)
    
    return render(request, 'classroom_core/group_form.html', {
        'form': form,
        'title': 'Редактировать группу',
        'group': group
    })

@login_required
def group_delete(request, group_id):
    """Удаление группы студентов"""
    group = get_object_or_404(StudentGroup, id=group_id)
    
    if not (request.user == group.created_by or request.user.profile.is_staff() or request.user.is_superuser):
        raise PermissionDenied
    
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f'Группа "{group_name}" успешно удалена')
        return redirect('classroom_core:group_list')
    
    return render(request, 'classroom_core/group_confirm_delete.html', {
        'group': group
    })

@login_required
def group_detail(request, group_id):
    """Детали группы студентов"""
    group = get_object_or_404(StudentGroup, id=group_id)
    
    students = group.students.all()
    
    # Пагинация студентов
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    
    return render(request, 'classroom_core/group_detail.html', context)

@login_required
def group_add_students(request, group_id):
    """Добавление студентов в группу"""
    group = get_object_or_404(StudentGroup, id=group_id)
    
    if not (request.user == group.created_by or request.user.profile.is_staff() or request.user.is_superuser):
        raise PermissionDenied
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('students')
        students_added = 0
        
        for student_id in student_ids:
            try:
                user = User.objects.get(id=student_id)
                if hasattr(user, 'profile') and user.profile.role == 'student':
                    user.profile.student_group = group
                    user.profile.save()
                    students_added += 1
            except User.DoesNotExist:
                continue
        
        messages.success(request, f'В группу добавлено {students_added} студентов')
        return redirect('classroom_core:group_detail', group_id=group.id)
    
    # Получаем студентов, которые еще не в группе
    available_students = User.objects.filter(
        profile__role='student',
        profile__student_group__isnull=True
    )
    
    context = {
        'group': group,
        'available_students': available_students,
    }
    
    return render(request, 'classroom_core/group_add_students.html', context)