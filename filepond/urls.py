from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt

from . import views


app_name = 'filepond'
urlpatterns = [
    url(
        regex=r"^process/$",
        view=csrf_exempt(views.UploadCreateView.as_view()),
        name="process",
    ),
    url(
        regex=r"^revert/$",
        view=csrf_exempt(views.UploadRevertView.as_view()),
        name="revert",
    ),
    url(
        regex=r"^get/(?P<pk>[0-9]+)/(?P<size>[\w]+)/$",
        view=views.FileView.as_view(),
        name="get",
    ),
]
