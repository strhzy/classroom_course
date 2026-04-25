from django.shortcuts import render ,redirect ,get_object_or_404 
from django.contrib.auth.decorators import login_required 
from django.contrib import messages 
from django.http import HttpResponse ,Http404 ,JsonResponse 
from django.core.exceptions import PermissionDenied ,ValidationError 
from django.db.models import Q 
from django.core.paginator import Paginator 
from django.contrib.auth.models import User
from . models import File ,FileCategory ,Tag ,FileComment ,FileVersion ,FileActivity ,UserStorageQuota 
from . forms import FileUploadForm ,FileEditForm ,FileVersionForm ,FileCommentForm ,FileCategoryForm ,TagForm ,FileSearchForm 
from . utils import extract_text_from_file ,generate_preview ,search_files ,get_user_storage_usage 
import os 
import requests
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import ExternalStorageConnection
from .models import FavoriteCollection, FavoriteCollectionItem, SharedWorkspace
from .yandex_disk import (
    get_authorize_url,
    exchange_code_for_token,
    list_files,
    get_disk_info,
    resource_exists,
    get_download_url,
    upload_file_bytes,
    delete_resource,
)
from .import_pipeline import import_yandex_file
import zipfile
import io
import json
from pathlib import Path
from pathlib import PurePosixPath


def get_yandex_connection(user, autocreate_from_social=False):
    connection = ExternalStorageConnection.objects.filter(
        user=user, provider="yandex_disk"
    ).first()
    if connection or not autocreate_from_social:
        return connection

    try:
        from allauth.socialaccount.models import SocialToken
    except Exception:
        return None

    social_token = (
        SocialToken.objects.filter(account__user=user, account__provider="yandex")
        .order_by("-id")
        .first()
    )
    if not social_token or not social_token.token:
        return None

    expires_at = social_token.expires_at if social_token.expires_at else timezone.now() + timezone.timedelta(days=30)
    connection, _ = ExternalStorageConnection.objects.update_or_create(
        user=user,
        provider="yandex_disk",
        defaults={
            "access_token": social_token.token,
            "refresh_token": social_token.token_secret or "",
            "expires_at": expires_at,
        },
    )
    return connection


def build_unique_title(user, original_name):
    base_name = (original_name or "").strip() or "file"
    stem, ext = os.path.splitext(base_name)
    stem = stem or "file"
    ext = ext or ""
    candidate = f"{stem}{ext}"
    counter = 1
    while File.objects.filter(uploaded_by=user, title=candidate).exists():
        candidate = f"{stem}{counter}{ext}"
        counter += 1
    return candidate


def sync_deleted_yandex_files_for_user(user):
    connection = get_yandex_connection(user, autocreate_from_social=True)
    if not connection:
        return
    yandex_files = File.objects.filter(
        uploaded_by=user,
        storage_provider="yandex_disk",
    ).exclude(yandex_path="")
    for file_obj in yandex_files:
        try:
            exists = resource_exists(connection.access_token, file_obj.yandex_path)
        except Exception:
            continue
        if not exists:
            file_obj.delete()

@login_required 
def file_list(request ):
    sync_deleted_yandex_files_for_user(request.user)
    storage_quota =get_user_storage_usage(request.user )
    yandex_connection = get_yandex_connection(request.user, autocreate_from_social=True)

    files =search_files(
    query =request.GET.get('query'),
    user =request.user ,
    file_types =[request.GET.get('file_type')]if request.GET.get('file_type')else None ,
    categories =[request.GET.get('category')]if request.GET.get('category')else None ,
    tags =request.GET.getlist('tags'),
    date_from =request.GET.get('date_from'),
    date_to =request.GET.get('date_to')
    )
    if request.GET.get('favorites_only'):
        files = files.filter(favorite=request.user)

    folders =File.objects.filter(
    Q(uploaded_by =request.user )|
    Q(visibility ='public')|
    Q(shared_with =request.user )
    ).distinct().filter(is_folder =True )

    sort_by =request.GET.get('sort','-uploaded_at')
    files =files.order_by(sort_by )

    paginator =Paginator(files ,20 )
    page_number =request.GET.get('page')
    page_obj =paginator.get_page(page_number )

    total_files =files.count()
    total_size =sum(f.file_size for f in files )

    context ={
    'page_obj':page_obj ,
    'folders':folders ,
    'search_form':FileSearchForm(request.GET ),
    'total_files':total_files ,
    'total_size':total_size ,
    'categories':FileCategory.objects.all(),
    'tags':Tag.objects.all(),
    'storage_quota':storage_quota ,
    'yandex_connected': bool(yandex_connection),
    }

    return render(request ,'file_manager/file_list.html',context )

@login_required 
def file_upload(request ):
    print("[file_upload] start", {"method": request.method, "user_id": request.user.id, "username": request.user.username})
    if request.method != 'POST':
        print("[file_upload] non-POST -> redirect file_list")
        return redirect('file_manager:file_list')

    storage_quota = get_user_storage_usage(request.user)
    print("[file_upload] quota", {
        "used_bytes": storage_quota.used_bytes,
        "total_quota_bytes": storage_quota.total_quota_bytes,
    })
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        print("[file_upload] no file in request.FILES", {"keys": list(request.FILES.keys())})
        messages.error(request, 'Файл не выбран')
        return redirect('file_manager:file_list')

    file_size = uploaded_file.size
    print("[file_upload] incoming file", {
        "name": uploaded_file.name,
        "size": file_size,
        "content_type": getattr(uploaded_file, "content_type", None),
    })
    if not storage_quota.has_enough_space(file_size):
        print("[file_upload] quota check failed")
        messages.error(request, f'Недостаточно места в хранилище. Доступно: {storage_quota.get_quota_display()}')
        return redirect('file_manager:file_list')

    file_name = PurePosixPath(uploaded_file.name).name
    unique_title = build_unique_title(request.user, file_name)
    yandex_connection = get_yandex_connection(request.user, autocreate_from_social=True)
    file_obj = None

    if yandex_connection:
        yandex_path = f"disk:/{unique_title}"
        print("[file_upload] yandex storage target", {"file_name": unique_title, "yandex_path": yandex_path})
        try:
            upload_file_bytes(yandex_connection.access_token, yandex_path, uploaded_file.read(), overwrite=True)
            file_obj = File.objects.create(
                title=unique_title,
                description="",
                uploaded_by=request.user,
                visibility="private",
                importance="main",
                is_folder=False,
                storage_provider="yandex_disk",
                yandex_path=yandex_path,
                file_size=file_size,
            )
            messages.success(request, "Файл успешно загружен на Яндекс.Диск")
            print("[file_upload] yandex save success", {"file_id": file_obj.id, "yandex_path": yandex_path})
        except Exception as exc:
            print("[file_upload] yandex save failed, fallback to local", {"error": repr(exc)})
            messages.warning(request, f"Не удалось загрузить на Яндекс.Диск, сохранено локально: {exc}")

    if not file_obj:
        print("[file_upload] local storage target", {"file_name": unique_title})
        try:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            file_obj = File(
                title=unique_title,
                description="",
                uploaded_by=request.user,
                visibility="private",
                importance="main",
                is_folder=False,
                storage_provider="local",
                yandex_path="",
                file_size=file_size,
            )
            file_obj.file.save(unique_title, uploaded_file, save=True)
            print("[file_upload] local save success", {"file_id": file_obj.id, "path": file_obj.file.name})
            messages.success(request, "Файл успешно загружен в локальное хранилище")
        except Exception as exc:
            print("[file_upload] local save failed", {"error": repr(exc)})
            messages.error(request, f"Не удалось сохранить файл: {exc}")
            return redirect('file_manager:file_list')

    try:
        FileActivity.log_activity(
            file=file_obj,
            user=request.user,
            activity_type='upload',
            description=f'File uploaded: {file_obj.title }'
        )
        print("[file_upload] activity logged", {"file_id": file_obj.id})
    except Exception as exc:
        print("[file_upload] activity log failed", {"error": repr(exc), "file_id": file_obj.id})

    try:
        storage_quota.update_usage()
        print("[file_upload] quota updated")
    except Exception as exc:
        print("[file_upload] quota update failed", {"error": repr(exc)})

    print("[file_upload] done", {"redirect_file_id": file_obj.id})
    return redirect('file_manager:file_detail', file_id=file_obj.id)

@login_required 
def file_detail(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    comments =file_obj.comments.filter(parent =None )

    comment_form =FileCommentForm()

    if request.user !=file_obj.uploaded_by :
        FileActivity.log_activity(
        file =file_obj ,
        user =request.user ,
        activity_type ='view',
        description =f'File viewed: {file_obj.title }'
        )

    context ={
    'file':file_obj ,
    'comments':comments ,
    'comment_form':comment_form ,
    'can_edit':file_obj.can_edit(request.user ),
    'can_delete':file_obj.can_delete(request.user ),
    'is_favorite':file_obj.is_favorite(request.user ),
    'favorite_collections': FavoriteCollection.objects.filter(user=request.user),
    'shared_workspaces': SharedWorkspace.objects.filter(participants=request.user),
    }

    return render(request ,'file_manager/file_detail.html',context )

@login_required 
def file_download(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise Http404
        download_url = get_download_url(connection.access_token, file_obj.yandex_path)
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        FileActivity.log_activity(
            file=file_obj,
            user=request.user,
            activity_type='download',
            description=f'File downloaded: {file_obj.title }',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        file_obj.increment_download()
        output = HttpResponse(response.content, content_type="application/octet-stream")
        output['Content-Disposition'] = f'attachment; filename="{file_obj.title}"'
        return output

    if file_obj.file and os.path.exists(file_obj.file.path):
        FileActivity.log_activity(file=file_obj, user=request.user, activity_type='download', description=f'File downloaded: {file_obj.title }', ip_address=request.META.get('REMOTE_ADDR'))
        file_obj.increment_download()
        with open(file_obj.file.path ,'rb')as fh :
            response =HttpResponse(fh.read(),content_type ="application/octet-stream")
            response ['Content-Disposition']=f'attachment; filename="{os.path.basename(file_obj.file.path)}"'
            return response
    raise Http404

@login_required 
def file_preview(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    file_ext = (file_obj.get_extension() or "").lower()
    content_type = 'application/octet-stream'
    if file_ext in ['txt']:
        content_type ='text/plain'
    elif file_ext in ['pdf']:
        content_type ='application/pdf'
    elif file_ext in ['jpg','jpeg']:
        content_type ='image/jpeg'
    elif file_ext in ['png']:
        content_type ='image/png'

    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise Http404
        download_url = get_download_url(connection.access_token, file_obj.yandex_path)
        resp = requests.get(download_url, timeout=60)
        resp.raise_for_status()
        response = HttpResponse(resp.content, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{file_obj.title}"'
        return response

    if file_obj.file and os.path.exists(file_obj.file.path):
        with open(file_obj.file.path ,'rb')as fh :
            response =HttpResponse(fh.read(),content_type =content_type )
            response ['Content-Disposition']=f'inline; filename="{os.path.basename(file_obj.file.path )}"'
            return response
    raise Http404

@login_required 
def file_edit(request ,file_id ):
    """Редактирование файла"""
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_edit(request.user ):
        raise PermissionDenied 

    students_queryset = User.objects.filter(profile__role='student').exclude(
        id=request.user.id
    ).order_by("username")

    if request.method =='POST':
        form =FileEditForm(request.POST ,instance =file_obj )
        form.fields ['shared_with'].queryset = students_queryset
        if form.is_valid():
            form.save()

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='edit',
            description =f'File edited: {file_obj.title }'
            )

            messages.success(request ,'Файл успешно обновлен')
            return redirect('file_manager:file_detail',file_id =file_obj.id )
    else :
        form =FileEditForm(instance =file_obj )
        form.fields ['shared_with'].queryset = students_queryset

    return render(request ,'file_manager/file_form.html',{
    'form':form ,
    'title':'Редактировать файл',
    'file':file_obj 
    })

@login_required 
def file_delete(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_delete(request.user ):
        raise PermissionDenied 

    if request.method =='POST':
        file_title =file_obj.title 
        file_size =file_obj.file_size 
        file_uploaded_by =file_obj.uploaded_by 

        yandex_path = file_obj.yandex_path
        local_path = file_obj.file.path if file_obj.file else None
        owner = file_obj.uploaded_by

        file_obj.delete()

        FileActivity.objects.create(
        user =request.user ,
        activity_type ='delete',
        description =f'File deleted: {file_title }'
        )

        if yandex_path:
            connection = get_yandex_connection(owner, autocreate_from_social=True)
            if connection:
                try:
                    delete_resource(connection.access_token, yandex_path, permanently=False)
                except Exception:
                    pass

        if local_path and os.path.exists(local_path):
            try :
                os.remove(local_path)
            except OSError :
                pass 

        storage_quota =get_user_storage_usage(request.user )
        storage_quota.update_usage()

        messages.success(request ,'Файл успешно удален')
        return redirect('file_manager:file_list')

    return render(request ,'file_manager/file_confirm_delete.html',{
    'file':file_obj 
    })

@login_required 
def file_version_create(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )


    if not file_obj.can_edit(request.user ):
        raise PermissionDenied 

    storage_quota =get_user_storage_usage(request.user )

    if request.method =='POST':
        form =FileVersionForm(request.POST ,request.FILES )
        if form.is_valid():
            file_size =request.FILES ['version_file'].size 
            if not storage_quota.has_enough_space(file_size ):
                messages.error(request ,f'Недостаточно места в хранилище для новой версии. Доступно: {storage_quota.get_quota_display()}')
                return redirect('file_manager:file_version_create',file_id =file_id )

            version =form.save(commit =False )
            version.file =file_obj 
            version.changed_by =request.user 
            version.version_number =file_obj.version +1 
            version.save()

            old_file_path =file_obj.file.path 
            file_obj.file =version.version_file 
            file_obj.version +=1 
            file_obj.save()

            try :
                extracted_text =extract_text_from_file(file_obj.file.path )
                file_obj.extracted_text =extracted_text 
                file_obj.save()
            except Exception as e :
                messages.warning(request ,f'Текст не извлечен: {e }')

            if os.path.exists(old_file_path ):
                os.remove(old_file_path )

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='version_create',
            description =f'New version {version.version_number } created: {form.cleaned_data.get("change_description","")}'
            )

            storage_quota.update_usage()

            messages.success(request ,'Новая версия файла создана')
            return redirect('file_manager:file_detail',file_id =file_obj.id )
    else :
        form =FileVersionForm()

    return render(request ,'file_manager/file_version_form.html',{
    'form':form ,
    'file':file_obj ,
    'storage_quota':storage_quota ,
    })

@login_required 
def folder_create(request ):
    if request.method =='POST':
        title =request.POST.get('title')
        description =request.POST.get('description','')
        parent_folder_id =request.POST.get('parent_folder')

        folder =File.objects.create(
        title =title ,
        description =description ,
        uploaded_by =request.user ,
        is_folder =True ,
        visibility ='private'
        )

        if parent_folder_id :
            parent_folder =get_object_or_404(File ,id =parent_folder_id ,is_folder =True )
            if parent_folder.can_edit(request.user ):
                folder.folder =parent_folder 
                folder.save()

        FileActivity.log_activity(
        file =folder ,
        user =request.user ,
        activity_type ='upload',
        description =f'Folder created: {folder.title }'
        )

        messages.success(request ,'Папка успешно создана')
        return redirect('file_manager:file_list')

    folders =File.objects.filter(uploaded_by =request.user ,is_folder =True )
    return render(request ,'file_manager/folder_form.html',{'folders':folders })

@login_required 
def favorite_toggle(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if file_obj.is_favorite(request.user ):
        file_obj.remove_from_favorites(request.user )
        messages.success(request ,'Файл удален из избранного')
        activity_type ='favorite_remove'
    else :
        file_obj.add_to_favorites(request.user )
        messages.success(request ,'Файл добавлен в избранное')
        activity_type ='favorite_add'

    FileActivity.log_activity(
    file =file_obj ,
    user =request.user ,
    activity_type =activity_type ,
    description =f'Favorite status toggled for: {file_obj.title }'
    )

    return redirect(request.META.get('HTTP_REFERER','file_manager:file_list'))

@login_required 
def file_comment_create(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if request.method =='POST':
        form =FileCommentForm(request.POST )
        if form.is_valid():
            comment =form.save(commit =False )
            comment.file =file_obj 
            comment.author =request.user 
            comment.save()

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='comment',
            description =f'Comment added to: {file_obj.title }'
            )

            messages.success(request ,'Комментарий добавлен')

        return redirect('file_manager:file_detail',file_id =file_id )

    return redirect('file_manager:file_detail',file_id =file_id )

@login_required 
def file_comment_delete(request ,comment_id ):
    comment =get_object_or_404(FileComment ,id =comment_id )

    if not comment.can_delete(request.user ):
        raise PermissionDenied 

    file_id =comment.file.id 
    comment.delete()

    FileActivity.log_activity(
    file =comment.file ,
    user =request.user ,
    activity_type ='comment',
    description =f'Comment deleted from: {comment.file.title }'
    )

    messages.success(request ,'Комментарий удален')
    return redirect('file_manager:file_detail',file_id =file_id )

@login_required 
def activity_log(request ):
    activities =FileActivity.objects.filter(user =request.user ).select_related('file','user')

    activity_type =request.GET.get('activity_type')
    if activity_type :
        activities =activities.filter(activity_type =activity_type )

    paginator =Paginator(activities ,20 )
    page_number =request.GET.get('page')
    page_obj =paginator.get_page(page_number )

    context ={
    'page_obj':page_obj ,
    'activity_types':FileActivity.ACTIVITY_TYPES ,
    'selected_activity_type':activity_type ,
    }

    return render(request ,'file_manager/activity_log.html',context )

@login_required 
def category_list(request ):
    categories =FileCategory.objects.all()
    return render(request ,'file_manager/category_list.html',{'categories':categories })

@login_required 
def category_create(request ):
    if request.method =='POST':
        form =FileCategoryForm(request.POST )
        if form.is_valid():
            form.save()
            messages.success(request ,'Категория создана')
            return redirect('file_manager:category_list')
    else :
        form =FileCategoryForm()

    return render(request ,'file_manager/category_form.html',{'form':form })

@login_required 
def tag_list(request ):
    tags =Tag.objects.all()
    return render(request ,'file_manager/tag_list.html',{'tags':tags })

@login_required 
def tag_create(request ):
    if request.method =='POST':
        form =TagForm(request.POST )
        if form.is_valid():
            form.save()
            messages.success(request ,'Тег создан')
            return redirect('file_manager:tag_list')
    else :
        form =TagForm()

    return render(request ,'file_manager/tag_form.html',{'form':form })

@login_required 
def get_storage_quota(request ):
    if request.method =='GET':
        yandex_connection = get_yandex_connection(request.user, autocreate_from_social=True)
        if yandex_connection:
            try:
                disk_info = get_disk_info(yandex_connection.access_token)
                used_bytes = int(disk_info.get("used_space", 0))
                total_quota_bytes = int(disk_info.get("total_space", 0))
                used_percentage = (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
                return JsonResponse({
                    'used_bytes': used_bytes,
                    'total_quota_bytes': total_quota_bytes,
                    'used_percentage': used_percentage,
                })
            except Exception:
                pass
        storage_quota =get_user_storage_usage(request.user )
        return JsonResponse({
        'used_bytes':storage_quota.used_bytes ,
        'total_quota_bytes':storage_quota.total_quota_bytes ,
        'used_percentage':storage_quota.get_used_percentage()
        })
    return JsonResponse({'error':'Method not allowed'},status =405 )


@login_required
def yandex_oauth_start(request):
    state = get_random_string(24)
    request.session["yandex_oauth_state"] = state
    authorize_url = get_authorize_url(
        settings.YANDEX_DISK_CLIENT_ID,
        settings.YANDEX_DISK_REDIRECT_URI or request.build_absolute_uri("/files/oauth/yandex/callback/"),
        state,
    )
    return redirect(authorize_url)


@login_required
def yandex_oauth_callback(request):
    state = request.GET.get("state")
    code = request.GET.get("code")
    if not state or state != request.session.get("yandex_oauth_state"):
        messages.error(request, "Неверный OAuth state")
        return redirect("file_manager:file_list")
    if not code:
        messages.error(request, "OAuth код не получен")
        return redirect("file_manager:file_list")

    try:
        token_data = exchange_code_for_token(
            settings.YANDEX_DISK_CLIENT_ID,
            settings.YANDEX_DISK_CLIENT_SECRET,
            code,
        )
    except Exception:
        messages.error(request, "Не удалось подключить Яндекс.Диск")
        return redirect("file_manager:file_list")

    expires_at = timezone.now() + timezone.timedelta(seconds=int(token_data.get("expires_in", 0)))
    ExternalStorageConnection.objects.update_or_create(
        user=request.user,
        provider="yandex_disk",
        defaults={
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": expires_at,
        },
    )
    messages.success(request, "Яндекс.Диск подключен")
    return redirect("file_manager:file_list")


@login_required
def yandex_disconnect(request):
    ExternalStorageConnection.objects.filter(user=request.user, provider="yandex_disk").delete()
    messages.success(request, "Яндекс.Диск отключен")
    return redirect("file_manager:file_list")


@login_required
def yandex_file_picker(request):
    connection = get_yandex_connection(request.user, autocreate_from_social=True)
    if not connection:
        messages.error(request, "Сначала подключите Яндекс.Диск")
        return redirect("file_manager:file_list")

    files = []
    try:
        files = [f for f in list_files(connection.access_token) if f.get("type") == "file"]
    except Exception:
        messages.error(request, "Не удалось получить список файлов с Яндекс.Диска")
        return redirect("file_manager:file_list")

    if request.method == "POST":
        selected_path = request.POST.get("path")
        selected_name = request.POST.get("name")
        assignment_id = request.POST.get("assignment_id") or request.GET.get("assignment_id")
        section_id = request.POST.get("section_id") or request.GET.get("section_id")
        if not selected_path or not selected_name:
            messages.error(request, "Файл не выбран")
            return redirect("file_manager:yandex_picker")
        download_url = get_download_url(connection.access_token, selected_path)
        if not download_url:
            messages.error(request, "Не удалось получить ссылку на скачивание")
            return redirect("file_manager:yandex_picker")
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        file_obj = import_yandex_file(request.user, selected_name, response.content)
        storage_quota = get_user_storage_usage(request.user)
        storage_quota.update_usage()
        if assignment_id:
            from classroom_core.models import Assignment, AssignmentFile
            assignment = Assignment.objects.filter(id=assignment_id).first()
            if assignment:
                AssignmentFile.objects.get_or_create(
                    assignment=assignment,
                    student=request.user,
                    file=file_obj,
                    defaults={"description": "Импортировано с Яндекс.Диска"},
                )
                messages.success(request, "Файл импортирован и прикреплен к заданию")
                return redirect("classroom_core:assignment_detail", assignment_id=assignment.id)
        if section_id:
            from classroom_core.models import CourseSection, CourseMaterial
            section = CourseSection.objects.filter(id=section_id).first()
            if section:
                CourseMaterial.objects.create(
                    section=section,
                    title=selected_name,
                    description="Импортировано с Яндекс.Диска",
                    material_type="link",
                    url=request.build_absolute_uri(file_obj.file.url),
                    is_visible=True,
                    status="published",
                )
                messages.success(request, "Файл импортирован и добавлен как материал курса")
                return redirect("classroom_core:course_detail", course_id=section.course_id)
        messages.success(request, "Файл импортирован из Яндекс.Диска")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    return render(request, "file_manager/yandex_picker.html", {"yandex_files": files})


@login_required
@require_http_methods(["POST"])
def yandex_export_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    if not file_obj.can_access(request.user):
        raise PermissionDenied

    connection = get_yandex_connection(request.user, autocreate_from_social=True)
    if not connection:
        messages.error(request, "Сначала подключите Яндекс.Диск")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    if not file_obj.file:
        messages.error(request, "Нельзя экспортировать папку или пустой файл")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    yandex_path = f"disk:/{file_obj.title}"
    try:
        with open(file_obj.file.path, "rb") as fh:
            upload_file_bytes(connection.access_token, yandex_path, fh.read(), overwrite=True)
    except Exception:
        messages.error(request, "Не удалось выгрузить файл на Яндекс.Диск")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    messages.success(request, "Файл выгружен на Яндекс.Диск")
    return redirect("file_manager:file_detail", file_id=file_obj.id)


@login_required
def download_all_files_archive(request):
    files = File.objects.filter(uploaded_by=request.user, is_folder=False)
    if files.count() == 0:
        messages.error(request, "Нет файлов для скачивания")
        return redirect("file_manager:file_list")
    else:
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_obj in files:
                try:
                    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
                        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
                        if not connection:
                            continue
                        href = get_download_url(connection.access_token, file_obj.yandex_path)
                        content = requests.get(href, timeout=60).content
                        archive.writestr(file_obj.title, content)
                    elif file_obj.file:
                        file_path = Path(file_obj.file.path)
                        if file_path.exists():
                            archive.write(file_path, arcname=file_path.name)
                except Exception:
                    continue
        archive_buffer.seek(0)
        response = HttpResponse(archive_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="portfolio_files.zip"'
        return response


@login_required
@require_http_methods(["POST"])
def favorite_collection_create(request):
    title = (request.POST.get("title") or "").strip()
    if not title:
        messages.error(request, "Название категории избранного обязательно")
    else:
        FavoriteCollection.objects.get_or_create(user=request.user, title=title)
        messages.success(request, "Категория избранного создана")
    return redirect(request.META.get("HTTP_REFERER", "file_manager:file_list"))


@login_required
@require_http_methods(["POST"])
def favorite_collection_add_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    collection_id = request.POST.get("collection_id")
    collection = get_object_or_404(FavoriteCollection, id=collection_id, user=request.user)
    FavoriteCollectionItem.objects.get_or_create(collection=collection, file=file_obj)
    messages.success(request, "Файл добавлен в категорию избранного")
    return redirect("file_manager:file_detail", file_id=file_id)


@login_required
@require_http_methods(["POST"])
def workspace_create(request):
    title = (request.POST.get("title") or "").strip()
    participant_username = (request.POST.get("participant") or "").strip()
    participant = User.objects.filter(username=participant_username).first()
    if not title or not participant:
        messages.error(request, "Укажите название и существующего пользователя")
        return redirect("file_manager:file_list")
    workspace = SharedWorkspace.objects.create(title=title, owner=request.user)
    workspace.participants.add(request.user, participant)
    messages.success(request, "Общий workspace создан")
    return redirect("file_manager:file_list")


@login_required
@require_http_methods(["POST"])
def workspace_add_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    workspace_id = request.POST.get("workspace_id")
    workspace = get_object_or_404(SharedWorkspace, id=workspace_id, participants=request.user)
    workspace.files.add(file_obj)
    if workspace.participants.exclude(id=request.user.id).exists():
        file_obj.shared_with.add(*workspace.participants.exclude(id=request.user.id))
        file_obj.visibility = "shared"
        file_obj.save(update_fields=["visibility"])
    messages.success(request, "Файл добавлен в общий workspace")
    return redirect("file_manager:file_detail", file_id=file_id)


@login_required
def backup_compare(request):
    backups_dir = Path(settings.BASE_DIR) / "backups"
    first = request.GET.get("first")
    second = request.GET.get("second")
    backups = sorted([p.name for p in backups_dir.glob("snapshot_*.zip")], reverse=True)
    diff = {"added": [], "removed": []}
    if first and second:
        first_set, second_set = set(), set()
        with zipfile.ZipFile(backups_dir / first, "r") as z1:
            first_set = set(z1.namelist())
        with zipfile.ZipFile(backups_dir / second, "r") as z2:
            second_set = set(z2.namelist())
        diff["added"] = sorted(list(second_set - first_set))
        diff["removed"] = sorted(list(first_set - second_set))
    return render(request, "file_manager/backup_compare.html", {"backups": backups, "diff": diff, "first": first, "second": second})