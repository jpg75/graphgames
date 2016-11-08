from functools import wraps
from flask import abort
from flask_login import current_user
from flask_socketio import disconnect

# def permission_required(permission):
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if not current_user.can(permission):
#                 abort(403)
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator


def authenticated_only(f):
    """
    Since 'login_required' decorator cannot be used with SocketIO event handlers, this decorator
    represents its equivalent.

    :param f:
    :return:
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_administrator():
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator
