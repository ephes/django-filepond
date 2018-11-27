from django.apps import apps
from django.http import HttpResponse
from django.db.utils import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DeleteView, DetailView

from .models import Upload
from .forms import get_model_form


def default_upload_handler(request):
    """
    Default upload handler saves files to uploads dir and
    return no other Model that should be notified about
    upload.
    """

    def get_upload_path(instance, filename):
        return f"uploads/{filename}"

    return get_upload_path, None


class UploadCreateView(LoginRequiredMixin, CreateView):
    def get_success_url(self):
        return None

    def form_valid(self, form):
        user_field = self.context["user_field"]
        upload_field_name = self.context["upload_field_name"]

        # save upload into target model
        model = form.save(commit=False)
        print("form valid model: ", model, getattr(model, upload_field_name).path)
        if user_field is not None:
            setattr(model, user_field, self.request.user)
        super().form_valid(form)

        # if target model != Upload, save an Upload instance, too
        upload_pk = model.pk
        if model.__class__ != Upload:
            upload = Upload.objects.create(
                original=getattr(model, upload_field_name),
                user=self.request.user,
                content_object=model,
            )
            upload_pk = upload.pk
            print("upload model: ", upload, upload.original.path)

        print("form valid model: ", model, getattr(model, upload_field_name).url)
        # return primary key of upload model, because we don't want
        # to have to guess which model to delete on post to revert endpoint
        return HttpResponse(f"{upload_pk}", status=201)

    def form_invalid(self, form):
        print("form invalid")
        print(form.errors)
        return super().form_invalid(form)

    def register_upload_app(self, request, *args, **kwargs):
        app_name = kwargs.get("app_name")
        if app_name is None:
            # if there's no app specified, use own model
            self.form_class, self.context = get_model_form(Upload, user_field="user")
            return

        # get the new form_class
        upload_handler = apps.get_app_config(app_name).module.upload_handler
        self.form_class, self.context = upload_handler(request)

        # move file input label to requested upload_field_name
        upload_field_name = self.context["upload_field_name"]
        if upload_field_name != "original":
            request.FILES[upload_field_name] = request.FILES.pop("original")[0]

        print("upload attr: ", upload_field_name)

    def post(self, request, *args, **kwargs):
        # default settings for model and form - they might be overwritten
        # by register_upload_app
        self.model = Upload

        # if file was uploaded by filepond, change the field name
        if "filepond" in request.FILES:
            request.FILES["original"] = request.FILES.pop("filepond")[0]
        self.register_upload_app(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class UploadRevertView(LoginRequiredMixin, DeleteView):
    model = Upload

    def delete(self, request, *args, **kwargs):
        image = self.model.objects.get(pk=int(request.body))
        if self.request.user == image.user:
            image.delete()
        return HttpResponse("", status=200)


class FileView(LoginRequiredMixin, DetailView):
    model = Upload
