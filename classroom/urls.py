from django .contrib import admin 
from django .urls import path ,include 
from django .conf import settings 
from django .conf .urls .static import static 

urlpatterns =[
    path ('admin/',admin .site .urls ),
    path ('',include ('classroom_core.urls',namespace ='classroom_core')),
    path ('files/',include ('file_manager.urls',namespace ='file_manager')),
]+static (settings .MEDIA_URL ,document_root =settings .MEDIA_ROOT )