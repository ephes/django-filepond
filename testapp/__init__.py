def upload_handler(request):
    from . import models
    from filepond.forms import get_model_form

    lookup = {}
    for ending in ("jpg", "jpeg", "png", "gif"):
        lookup[ending] = (models.LocalImage, "image", "owner")

    for ending in ("m4a", "mp3"):
        lookup[ending] = (models.LocalAudio, ending, "owner")

    file_name = str(request.FILES["original"])
    ending = file_name.lower().split(".")[-1]
    print("request filename: ", file_name, ending)
    local_model, upload_field_name, user_field = lookup[ending]
    return get_model_form(
        local_model, upload_field_name=upload_field_name, user_field=user_field
    )
