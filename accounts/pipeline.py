# accounts/pipeline.py
def set_name_from_google(backend, user, response, *args, **kwargs):
    if backend.name == 'google-oauth2' and not user.name:
        user.name = response.get('name', '')
        user.save()
    return {'user': user}