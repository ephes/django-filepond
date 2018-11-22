from django.http import HttpResponse
from django.db.utils import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, DeleteView, DetailView

from .models import Upload
from .forms import UploadForm

class UploadCreateView(LoginRequiredMixin, CreateView):
    model = Upload
    form_class = UploadForm

    def get_success_url(self):
        return None

    def form_valid(self, form):
        model = form.save(commit=False)
        model.user = self.request.user
        try:
            super().form_valid(form)
            return HttpResponse(f"{model.pk}", status=201)
        except IntegrityError as e:
            return HttpResponse("This file was already uploaded!", status=409)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        # if file was uploaded by filepond, change the field name
        if "filepond" in request.FILES:
            request.FILES["original"] = request.FILES.pop("filepond")[0]
        return super().post(request, *args, **kwargs)


class UploadRevertView(LoginRequiredMixin, DeleteView):
    model = Upload

    def delete(self, request, *args, **kwargs):
        image = self.model.objects.get(pk=int(request.body))
        if self.request.user == image.user:
            res = image.delete()
        return HttpResponse("", status=200)


class FileView(LoginRequiredMixin, DetailView):
    model = Upload
