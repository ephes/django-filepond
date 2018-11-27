from django.apps import AppConfig


def up_handler_factory(forms):
    def upload_handler(request):
        return forms.TestImageForm


class TestappConfig(AppConfig):
    name = "testapp"


#    def ready(self):
#        print("reaaaaaaaaaaaaaaaaaaaaaaaaaaaaaady")
#        from . import forms
#        self.module.upload_handler = upload_handler_factory(forms)
#        print("module upload handler: ", self.module.upload_handler)
