def next_redirect(request):
    """
    Safely provide 'next' in template context without triggering
    VariableDoesNotExist exceptions on QueryDict key lookups.
    """
    next_val = ''
    if request:
        next_val = (request.POST.get('next') or request.GET.get('next') or '').strip()
    return {'next': next_val}
