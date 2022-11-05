from django.urls import include, path

urlpatterns = [path("", include("filepond.urls", namespace="filepond"))]
