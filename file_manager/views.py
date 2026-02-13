from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from .models import File, FileComment, FileVersion, FileActivity
from .forms import FileUploadForm, FileEditForm, FileVersionForm, FileCommentForm, FileSearchForm
from classroom_core.models import Course
from .utils import extract_text_from_file, generate_preview
import os
from django.http import FileResponse
from django.utils.encoding import smart_str

@login_required
def file_list(request):
    files = File.objects.filter(
        Q(uploaded_by=request.user) | 
        Q(visibility='public') | 
        Q(shared_with=request.user)
    ).distinct().filter(is_folder=False)
    
    search_form = FileSearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        file_type = search_form.cleaned_data.get('file_type')
        course = search_form.cleaned_data.get('course')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        favorites_only = search_form.cleaned_data.get('favorites_only')
        
        if query:
            files = files.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(extracted_text__icontains=query)
            )
        
        if file_type:
            files = files.filter(file_type=file_type)
        
        if course:
            files = files.filter(course=course)
        
        if date_from:
            files = files.filter(uploaded_at__date__gte=date_from)
        
        if date_to:
            files = files.filter(uploaded_at__date__lte=date_to)
        
        if favorites_only:
            files = files.filter(favorite=request.user)
    
    folders = File.objects.filter(
        Q(uploaded_by=request.user) | 
        Q(visibility='public') | 
        Q(shared_with=request.user)
    ).distinct().filter(is_folder=True)
    
    sort_by = request.GET.get('sort', '-uploaded_at')
    files = files.order_by(sort_by)
    
    paginator = Paginator(files, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total_files = files.count()
    total_size = sum(f.file_size for f in files)
    
    context = {
        'page_obj': page_obj,
        'folders': folders,
        'search_form': search_form,
        'total_files': total_files,
        'total_size': total_size,
        'courses': Course.objects.all(),
    }
    
    return render(request, 'file_manager/file_list.html', context)

@login_required
def file_upload(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.uploaded_by = request.user
            
            if file_obj.folder and not file_obj.folder.can_edit(request.user):
                messages.error(request, 'Вы не можете добавлять файлы в эту папку')
                return redirect('file_manager:file_upload')
            
            file_obj.save()
            form.save_m2m()
            
            try:
                file_path = file_obj.file.path
                extracted_text = extract_text_from_file(file_path)
                file_obj.extracted_text = extracted_text
                file_obj.save()
                
                if file_obj.file_type in ['jpg', 'png', 'pdf']:
                    preview_path = generate_preview(file_path, os.path.dirname(file_path))
                    if preview_path:
                        file_obj.has_preview = True
                        file_obj.save()
                
                messages.success(request, 'Файл успешно загружен')
            except Exception as e:
                messages.warning(request, f'Файл загружен, но текст не извлечен: {e}')
            
            FileActivity.objects.create(
                file=file_obj,
                user=request.user,
                activity_type='upload',
                description=f'File uploaded: {file_obj.title}'
            )
            
            return redirect('file_manager:file_detail', file_id=file_obj.id)
    else:
        form = FileUploadForm()
        form.fields['folder'].queryset = File.objects.filter(
            uploaded_by=request.user,
            is_folder=True
        )
        form.fields['shared_with'].queryset = form.fields['shared_with'].queryset.exclude(
            id=request.user.id
        )
    
    return render(request, 'file_manager/file_form.html', {
        'form': form,
        'title': 'Загрузить файл'
    })

@login_required
def file_detail(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    
    comments = file_obj.comments.filter(parent=None)
    comment_form = FileCommentForm()
    
    if request.user != file_obj.uploaded_by:
        FileActivity.objects.create(
            file=file_obj,
            user=request.user,
            activity_type='view',
            description=f'File viewed: {file_obj.title}'
        )
    
    context = {
        'file': file_obj,
        'comments': comments,
        'comment_form': comment_form,
        'can_edit': file_obj.can_edit(request.user),
        'can_delete': file_obj.can_delete(request.user),
        'is_favorite': file_obj.is_favorite(request.user),
    }
    
    return render(request, 'file_manager/file_detail.html', context)


@login_required
def file_download(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)

    if not file_obj.can_access(request.user):
        raise PermissionDenied

    if not file_obj.file:
        raise Http404

    FileActivity.objects.create(
        file=file_obj,
        user=request.user,
        activity_type='download',
        description=f'File downloaded: {file_obj.title}'
    )

    file_obj.increment_download()

    response = FileResponse(
        file_obj.file.open('rb'),
        as_attachment=True,
        filename=smart_str(os.path.basename(file_obj.file.name))
    )

    return response

@login_required
def file_preview(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)

    if not file_obj.can_access(request.user):
        raise PermissionDenied

    if not file_obj.file:
        raise Http404

    ext = file_obj.file.name.split('.')[-1].lower()

    content_types = {
        'txt': 'text/plain',
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
    }

    content_type = content_types.get(ext, 'application/octet-stream')

    response = FileResponse(
        file_obj.file.open('rb'),
        content_type=content_type
    )

    response['Content-Disposition'] = (
        f'inline; filename="{smart_str(os.path.basename(file_obj.file.name))}"'
    )

    return response

@login_required
def file_edit(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_edit(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = FileEditForm(request.POST, instance=file_obj)
        if form.is_valid():
            form.save()
            
            FileActivity.objects.create(
                file=file_obj,
                user=request.user,
                activity_type='edit',
                description=f'File edited: {file_obj.title}'
            )
            
            messages.success(request, 'Файл успешно обновлен')
            return redirect('file_manager:file_detail', file_id=file_obj.id)
    else:
        form = FileEditForm(instance=file_obj)
        form.fields['shared_with'].queryset = form.fields['shared_with'].queryset.exclude(
            id=request.user.id
        )
    
    return render(request, 'file_manager/file_form.html', {
        'form': form,
        'title': 'Редактировать файл',
        'file': file_obj
    })

@login_required
def file_delete(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_delete(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        file_obj.delete()
        
        FileActivity.objects.create(
            file=file_obj,
            user=request.user,
            activity_type='delete',
            description=f'File deleted: {file_obj.title}'
        )
        
        messages.success(request, 'Файл успешно удален')
        return redirect('file_manager:file_list')
    
    return render(request, 'file_manager/file_list.html')

@login_required
def file_version_create(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_edit(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = FileVersionForm(request.POST, request.FILES)
        if form.is_valid():
            version = form.save(commit=False)
            version.file = file_obj
            version.changed_by = request.user
            version.version_number = file_obj.version + 1
            version.save()
            
            old_file_path = file_obj.file.path
            file_obj.file = version.version_file
            file_obj.version += 1
            file_obj.save()
            
            try:
                extracted_text = extract_text_from_file(file_obj.file.path)
                file_obj.extracted_text = extracted_text
                file_obj.save()
            except Exception as e:
                messages.warning(request, f'Текст не извлечен: {e}')
            
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            messages.success(request, 'Новая версия файла создана')
            return redirect('file_manager:file_detail', file_id=file_obj.id)
    else:
        form = FileVersionForm()
    
    return render(request, 'file_manager/file_version_form.html', {
        'form': form,
        'file': file_obj
    })

@login_required
def folder_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        parent_folder_id = request.POST.get('parent_folder')
        
        folder = File.objects.create(
            title=title,
            description=description,
            uploaded_by=request.user,
            is_folder=True,
            visibility='private'
        )
        
        if parent_folder_id:
            parent_folder = get_object_or_404(File, id=parent_folder_id, is_folder=True)
            if parent_folder.can_edit(request.user):
                folder.folder = parent_folder
                folder.save()
        
        messages.success(request, 'Папка успешно создана')
        return redirect('file_manager:file_list')
    
    folders = File.objects.filter(uploaded_by=request.user, is_folder=True)
    return render(request, 'file_manager/folder_form.html', {'folders': folders})

@login_required
def favorite_toggle(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    
    if file_obj.is_favorite(request.user):
        file_obj.remove_from_favorites(request.user)
        messages.success(request, 'Файл удален из избранного')
    else:
        file_obj.add_to_favorites(request.user)
        messages.success(request, 'Файл добавлен в избранное')
    
    return redirect(request.META.get('HTTP_REFERER', 'file_manager:file_list'))

@login_required
def file_comment_create(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = FileCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.file = file_obj
            comment.author = request.user
            comment.save()
            
            FileActivity.objects.create(
                file=file_obj,
                user=request.user,
                activity_type='comment',
                description=f'Comment added to: {file_obj.title}'
            )
            
            messages.success(request, 'Комментарий добавлен')
        
        return redirect('file_manager:file_detail', file_id=file_id)
    
    return redirect('file_manager:file_detail', file_id=file_id)

@login_required
def file_comment_delete(request, comment_id):
    comment = get_object_or_404(FileComment, id=comment_id)
    
    if not comment.can_delete(request.user):
        raise PermissionDenied
    
    file_id = comment.file.id
    comment.delete()
    
    messages.success(request, 'Комментарий удален')
    return redirect('file_manager:file_detail', file_id=file_id)

@login_required
def category_list(request):
    # Удалено: категории больше не используются
    return redirect('file_manager:file_list')

@login_required
def category_create(request):
    # Удалено: категории больше не используются
    return redirect('file_manager:file_list')

@login_required
def tag_list(request):
    # Удалено: теги больше не используются
    return redirect('file_manager:file_list')

@login_required
def tag_create(request):
    # Удалено: теги больше не используются
    return redirect('file_manager:file_list')


@login_required
def courses_overview(request):
    # Показать список курсов с краткой статистикой файлов
    courses = Course.objects.all()
    course_data = []
    for c in courses:
        files_count = c.files.count()
        course_data.append({'course': c, 'files_count': files_count})
    return render(request, 'file_manager/course_list.html', {'courses': course_data})


@login_required
def course_files(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    files = File.objects.filter(course=course, is_folder=False).filter(
        Q(uploaded_by=request.user) | Q(visibility='public') | Q(shared_with=request.user)
    ).distinct()

    paginator = Paginator(files.order_by('-uploaded_at'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'file_manager/file_list.html', {
        'page_obj': page_obj,
        'folders': File.objects.filter(course=course, is_folder=True),
        'search_form': FileSearchForm(),
        'total_files': files.count(),
        'total_size': sum(f.file_size for f in files),
        'courses': Course.objects.all(),
        'current_course': course,
    })