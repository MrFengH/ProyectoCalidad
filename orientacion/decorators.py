from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .nav import NAV_BY_ID, nav_ids


def role_required(page_id):
    """Exige sesión iniciada y que el rol del usuario tenga acceso a `page_id`
    (equivalente a requireAuth(pageId) de app.js). Si el rol no tiene acceso,
    redirige a la primera página que sí le corresponde."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            ids = nav_ids(request.user.rol)
            if page_id not in ids:
                primero = NAV_BY_ID[ids[0]] if ids else NAV_BY_ID['inicio']
                return redirect(primero['url'])
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
