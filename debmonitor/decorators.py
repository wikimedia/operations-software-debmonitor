def verify_clients(arg):
    """Set an attribute to the view function to mark that it requires client validation.

    It can be called without arguments, that will set the whole view or class-based view, or with an argument
    (list or tuple) that lists all the HTTP methods that require validation. The latter is useful in class-based views.
    """
    if callable(arg):  # Decorator was called without parameter, require all methods to be verified
        func = arg
        func.debmonitor_verify_clients = True
        return func
    else:  # Decorator was called with parameter, specify which methods must be verified
        if type(arg) not in (list, tuple):
            raise RuntimeError(
                'Decorator verify_clients parameter must be a list or tuple, got {obj_type}'.format(obj_type=type(arg)))

        def wrapper(func):
            func.debmonitor_verify_clients_methods = arg
            return func

        return wrapper
