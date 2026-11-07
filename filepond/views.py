import logging

from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.uploadedfile import UploadedFile
from django.db import models, router, transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DeleteView, DetailView

from .forms import get_model_form
from .models import Upload


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

    def get_form_kwargs(self):
        """If an instance is in context, add it to form creation and
        switch from create to update."""
        form_kwargs = super().get_form_kwargs()
        if "instance" in self.context:
            form_kwargs["instance"] = self.context["instance"]
        return form_kwargs

    def form_valid(self, form):
        user_field = self.context["user_field"]
        upload_field_name = self.context["upload_field_name"]

        model = form.save(commit=False)
        if user_field is not None:
            setattr(model, user_field, self.request.user)
        using = router.db_for_write(type(model), instance=model)
        created_files = []
        try:
            with transaction.atomic(using=using):
                # Save incoming files explicitly so their final storage keys are
                # known even if the subsequent model/registration save fails.
                for field in model._meta.fields:
                    incoming = form.cleaned_data.get(field.name)
                    if isinstance(field, models.FileField) and isinstance(incoming, UploadedFile):
                        stored = getattr(model, field.name)
                        stored.save(incoming.name, incoming, save=False)
                        created_files.append((stored.storage, stored.name))
                model.save(using=using)
                form.save_m2m()
                self.object = model
                upload_pk = model.pk
                if model.__class__ != Upload:
                    upload = Upload.objects.using(using).create(
                        original=getattr(model, upload_field_name).name,
                        user=self.request.user,
                        content_object=model,
                    )
                    upload_pk = upload.pk
        except Exception:
            # The savepoint has rolled back; never remove old/shared keys.
            for storage, name in created_files:
                delete_unreferenced_file(storage, name, using)
            raise

        # return primary key of upload model, because we don't want
        # to have to guess which model to delete on post to revert endpoint
        return HttpResponse(f"{upload_pk}", status=201)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def register_upload_app(self, request, *args, **kwargs):
        app_name = kwargs.get("app_name")
        if app_name is None:
            # if there's no app specified, use own model
            self.form_class, self.context = get_model_form(Upload, user_field="user")
            return

        # get the new form_class
        try:
            app = apps.get_app_config(app_name)
        except LookupError:
            raise Http404("Unsupported upload application") from None
        upload_handler = getattr(app.module, "upload_handler", None)
        if not callable(upload_handler):
            raise Http404("Unsupported upload application")
        self.form_class, self.context = upload_handler(request)

        # move file input label to requested upload_field_name
        upload_field_name = self.context["upload_field_name"]
        if upload_field_name != "original":
            request.FILES[upload_field_name] = request.FILES.pop("original")[0]

    def post(self, request, *args, **kwargs):
        if len(request.FILES) != 1 or not any(name in request.FILES for name in ("filepond", "original")):
            return HttpResponseBadRequest("Invalid upload")
        input_name = "filepond" if "filepond" in request.FILES else "original"
        if len(request.FILES.getlist(input_name)) != 1:
            return HttpResponseBadRequest("Invalid upload")
        # if file was uploaded by filepond, change the field name
        if "filepond" in request.FILES:
            request.FILES["original"] = request.FILES.pop("filepond")[0]
        self.register_upload_app(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class UploadRevertView(LoginRequiredMixin, DeleteView):
    model = Upload

    def post(self, request, *args, **kwargs):
        # AutoField/BigAutoField IDs fit in a signed 64-bit database integer.
        body = request.body
        if not 1 <= len(body) <= 19 or not body.isdigit() or not 0 < int(body) <= 2**63 - 1:
            return HttpResponseBadRequest("Invalid upload identifier")
        using = router.db_for_write(self.model)
        with transaction.atomic(using=using):
            upload = get_object_or_404(
                self.model.objects.using(using).select_for_update(), pk=int(body), user=request.user
            )
            storage, name = upload.original.storage, upload.original.name
            if upload.content_object is not None:
                upload.content_object.delete(using=using)
            upload.delete(using=using)
            transaction.on_commit(lambda: delete_unreferenced_file(storage, name, using), using=using)
        return HttpResponse("", status=200)

    # Filepond's default revert method is DELETE; older integrations use POST.
    delete = post


def delete_unreferenced_file(storage, name, using):
    """Delete an owned key only when no registered FileField still references it."""
    if not name:
        return
    try:
        for model in apps.get_models():
            if not router.allow_migrate_model(using, model):
                continue
            for field in model._meta.fields:
                if isinstance(field, models.FileField) and field.storage is storage:
                    if model._base_manager.using(using).filter(**{field.name: name}).exists():
                        return
        storage.delete(name)
    except Exception:
        # Report orphan cleanup for operator retry.
        logging.getLogger(__name__).exception("Unable to remove upload storage key %r", name)


class FileView(LoginRequiredMixin, DetailView):
    model = Upload

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
