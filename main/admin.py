from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import *


class MessageAdmin(admin.ModelAdmin):
    fields = ['code', 
              'description', 'text_ru', 'text_en']

    def has_delete_permission(self, request, obj=None):
        return False


class WhitePhoneResource(resources.ModelResource):
    class Meta:
        model = WhitePhone
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('phone_number_text',)
        fields = ('phone_number_text',)


class WhitePhoneAdmin(ImportExportModelAdmin):
    resource_class = WhitePhoneResource

admin.site.register(WhitePhone, WhitePhoneAdmin)
admin.site.register(Category)
admin.site.register(Question)
admin.site.register(ViberUser)
admin.site.register(Message, MessageAdmin)
