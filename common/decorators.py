from functools import wraps
from django.http import HttpResponseForbidden


def skip_signal():
    def _skip_signal(signal_func):
        @wraps(signal_func)
        def _decorator(sender, instance, **kwargs):
            if hasattr(instance, 'skip_signal'):
                return None
            return signal_func(sender, instance, **kwargs)

        return _decorator

    return _skip_signal


def group_required(allowed_group_ids=None):
    def decorator(view):
        def wrapper(request, *args, **kwargs):
            user = request.user
            if any(item in allowed_group_ids for item in user.groups.values_list('id', flat=True)) or user.is_superuser:
                return view(request, *args, **kwargs)
            else:
                return HttpResponseForbidden("You don't have permission to perform this action.")
        return wrapper
    return decorator