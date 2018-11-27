def upload_handler(request):
    from . import models
    from filepond.forms import get_model_form

    return get_model_form(
        models.LocalImage, upload_field_name="image", user_field="owner"
    )
