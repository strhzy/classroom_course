from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.core.paginator import Paginator
from .models import File, FileCategory, Tag, FileComment, FileVersion, FileActivity, UserStorageQuota
from .forms import FileUploadForm, FileEditForm, FileVersionForm, FileCommentForm, FileCategoryForm, TagForm, FileSearchForm
from .utils import extract_text_from_file, generate_preview, search_files, get_user_storage_usage
import os

@login_required
def file_list(request):
    storage_quota = get_user_storage_usage(request.user)
    
    files = search_files(
        query=request.GET.get('query'),
        user=request.user,
        file_types=[request.GET.get('file_type')] if request.GET.get('file_type') else None,
        categories=[request.GET.get('category')] if request.GET.get('category') else None,
        tags=request.GET.getlist('tags'),
        date_from=request.GET.get('date_from'),
        date_to=request.GET.get('date_to')
    )
    
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
        'search_form': FileSearchForm(request.GET),
        'total_files': total_files,
        'total_size': total_size,
        'categories': FileCategory.objects.all(),
        'tags': Tag.objects.all(),
        'storage_quota': storage_quota,
    }
    
    return render(request, 'file_manager/file_list.html', context)

@login_required
def file_upload(request):
    storage_quota = get_user_storage_usage(request.user)
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_size = request.FILES['file'].size
            if not storage_quota.has_enough_space(file_size):
                messages.error(request, f'Недостаточно места в хранилище. Доступно: {storage_quota.get_quota_display()}')
                return redirect('file_manager:file_upload')
            
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
            
            FileActivity.log_activity(
                file=file_obj,
                user=request.user,
                activity_type='upload',
                description=f'File uploaded: {file_obj.title}'
            )
            
            storage_quota.update_usage()
            
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
        'title': 'Загрузить файл',
        'storage_quota': storage_quota,
    })

@login_required
def file_detail(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    
    comments = file_obj.comments.filter(parent=None)
    
    comment_form = FileCommentForm()
    
    if request.user != file_obj.uploaded_by:
        FileActivity.log_activity(
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
    
    file_path = file_obj.file.path
    
    if os.path.exists(file_path):
        FileActivity.log_activity(
            file=file_obj,
            user=request.user,
            activity_type='download',
            description=f'File downloaded: {file_obj.title}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        file_obj.increment_download()
        
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    
    raise Http404

@login_required
def file_preview(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    
    file_path = file_obj.file.path
    
    if os.path.exists(file_path):
        file_ext = file_obj.file.name.split('.')[-1].lower()
        content_type = ''
        
        if file_ext in ['txt']:
            content_type = 'text/plain'
        elif file_ext in ['pdf']:
            content_type = 'application/pdf'
        elif file_ext in ['jpg', 'jpeg']:
            content_type = 'image/jpeg'
        elif file_ext in ['png']:
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'
        
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
            return response
    
    raise Http404

@login_required
def file_edit(request, file_id):
    """Редактирование файла"""
    file_obj = get_object_or_404(File, id=file_id)
    
    if not file_obj.can_edit(request.user):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = FileEditForm(request.POST, instance=file_obj)
        if form.is_valid():
            form.save()
            
            FileActivity.log_activity(
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
        file_title = file_obj.title
        file_size = file_obj.file_size
        file_uploaded_by = file_obj.uploaded_by
        
        file_path = None
        if file_obj.file:
            file_path = file_obj.file.path
        
        file_obj.delete()
        
        FileActivity.objects.create(
            user=request.user,
            activity_type='delete',
            description=f'File deleted: {file_title}'
        )
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        storage_quota = get_user_storage_usage(request.user)
        storage_quota.update_usage()
        
        messages.success(request, 'Файл успешно удален')
        return redirect('file_manager:file_list')
    
    return render(request, 'file_manager/file_confirm_delete.html', {
        'file': file_obj
    })

@login_required
def file_version_create(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    
    # Проверка прав
    if not file_obj.can_edit(request.user):
        raise PermissionDenied
    
    storage_quota = get_user_storage_usage(request.user)
    
    if request.method == 'POST':
        form = FileVersionForm(request.POST, request.FILES)
        if form.is_valid():
            file_size = request.FILES['version_file'].size
            if not storage_quota.has_enough_space(file_size):
                messages.error(request, f'Недостаточно места в хранилище для новой версии. Доступно: {storage_quota.get_quota_display()}')
                return redirect('file_manager:file_version_create', file_id=file_id)
            
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
            
            FileActivity.log_activity(
                file=file_obj,
                user=request.user,
                activity_type='version_create',
                description=f'New version {version.version_number} created: {form.cleaned_data.get("change_description", "")}'
            )
            
            storage_quota.update_usage()
            
            messages.success(request, 'Новая версия файла создана')
            return redirect('file_manager:file_detail', file_id=file_obj.id)
    else:
        form = FileVersionForm()
    
    return render(request, 'file_manager/file_version_form.html', {
        'form': form,
        'file': file_obj,
        'storage_quota': storage_quota,
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
        
        FileActivity.log_activity(
            file=folder,
            user=request.user,
            activity_type='upload',
            description=f'Folder created: {folder.title}'
        )
        
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
        activity_type = 'favorite_remove'
    else:
        file_obj.add_to_favorites(request.user)
        messages.success(request, 'Файл добавлен в избранное')
        activity_type = 'favorite_add'
    
    FileActivity.log_activity(
        file=file_obj,
        user=request.user,
        activity_type=activity_type,
        description=f'Favorite status toggled for: {file_obj.title}'
    )
    
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
            
            FileActivity.log_activity(
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
    
    FileActivity.log_activity(
        file=comment.file,
        user=request.user,
        activity_type='comment',
        description=f'Comment deleted from: {comment.file.title}'
    )
    
    messages.success(request, 'Комментарий удален')
    return redirect('file_manager:file_detail', file_id=file_id)

@login_required
def activity_log(request):
    activities = FileActivity.objects.filter(user=request.user).select_related('file', 'user')
    
    activity_type = request.GET.get('activity_type')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'activity_types': FileActivity.ACTIVITY_TYPES,
        'selected_activity_type': activity_type,
    }
    
    return render(request, 'file_manager/activity_log.html', context)

@login_required
def category_list(request):
    categories = FileCategory.objects.all()
    return render(request, 'file_manager/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    if request.method == 'POST':
        form = FileCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория создана')
            return redirect('file_manager:category_list')
    else:
        form = FileCategoryForm()
    
    return render(request, 'file_manager/category_form.html', {'form': form})

@login_required
def tag_list(request):
    tags = Tag.objects.all()
    return render(request, 'file_manager/tag_list.html', {'tags': tags})

@login_required
def tag_create(request):
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тег создан')
            return redirect('file_manager:tag_list')
    else:
        form = TagForm()
    
    return render(request, 'file_manager/tag_form.html', {'form': form})

@login_required
def get_storage_quota(request):
    if request.method == 'GET':
        storage_quota = get_user_storage_usage(request.user)
        return JsonResponse({
            'used_bytes': storage_quota.used_bytes,
            'total_quota_bytes': storage_quota.total_quota_bytes,
            'used_percentage': storage_quota.get_used_percentage()
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)