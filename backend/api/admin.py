from django.contrib import admin

# import your model
from .models import Image, Annotation, Profile


class ImageAdmin(admin.ModelAdmin):
    model = Image
    list_display = ('img_id', 'extension', 'img_path')
    
class AnnotationAdmin(admin.ModelAdmin):
    model = Annotation
    list_display = ('id', 'annotator', 'image')    

class ProfileAdmin(admin.ModelAdmin):
    model = Profile
    list_display = ('user', 'is_test')
    
# register it
admin.site.register(Image, ImageAdmin)
admin.site.register(Annotation, AnnotationAdmin)
admin.site.register(Profile, ProfileAdmin)