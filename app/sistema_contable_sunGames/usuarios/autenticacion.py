from django.contrib.auth import login
from django.contrib.auth.backends import AllowAllUsersModelBackend
from django.db import DatabaseError

from .exceptions import CredencialesInvalidasError, ServicioAutenticacionError

SESSION_BACKEND = "django.contrib.auth.backends.ModelBackend"


class AutenticadorDjango:
    """Adaptador del sistema de autenticación de Django.

    Usa AllowAllUsersModelBackend para que el servicio distinga una cuenta
    inactiva de unas credenciales incorrectas; la sesión se abre con
    ModelBackend, que rechaza cuentas inactivas en peticiones posteriores.
    """

    def __init__(self):
        self._backend = AllowAllUsersModelBackend()

    def verificar_credenciales(self, request, username, password):
        try:
            usuario = self._backend.authenticate(
                request, username=username, password=password
            )
        except DatabaseError as exc:
            raise ServicioAutenticacionError() from exc
        if usuario is None:
            raise CredencialesInvalidasError()
        return usuario

    def abrir_sesion(self, request, usuario):
        try:
            login(request, usuario, backend=SESSION_BACKEND)
        except DatabaseError as exc:
            raise ServicioAutenticacionError() from exc
