from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = "filepond"
urlpatterns = [
    path("process", view=csrf_exempt(views.UploadCreateView.as_view()), name="process"),
    path(
        # process, but give an app name to dispatch the upload to
        "process/<path:app_name>",
        view=csrf_exempt(views.UploadCreateView.as_view()),
        name="process",
    ),
    path(
        "revert/",
        view=csrf_exempt(views.UploadRevertView.as_view()),
        name="revert",
    ),
    re_path(
        r"^get/(?P<pk>[0-9]+)/(?P<size>[\w]+)/$",
        view=views.FileView.as_view(),
        name="get",
    ),
]
