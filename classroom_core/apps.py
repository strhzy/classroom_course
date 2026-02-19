from django.apps import AppConfig 

class ClassroomCoreConfig(AppConfig ):
    default_auto_field ='django.db.models.BigAutoField'
    name ='classroom_core'

    def ready(self ):
        import classroom_core.signals 