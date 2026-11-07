from django.db import IntegrityError, transaction

from .exceptions import UsuarioDuplicadoError, UsuarioNoEncontradoError
from .models import Usuario


class UsuarioRepository:
    def existe_username(self, username):
        return Usuario.objects.filter(username=username).exists()

    def obtener_por_username(self, username):
        try:
            return Usuario.objects.get(username=username)
        except Usuario.DoesNotExist as exc:
            raise UsuarioNoEncontradoError() from exc

    def listar(self):
        return Usuario.objects.order_by("username")

    def crear(self, *, username, nombre_completo, rol):
        usuario = Usuario(
            username=username, nombre_completo=nombre_completo, rol=rol
        )
        # TODO(CU-02.1): sin contraseña utilizable hasta definir cómo se
        # establece la contraseña de usuarios nuevos.
        usuario.set_unusable_password()
        try:
            with transaction.atomic():
                usuario.save()
        except IntegrityError as exc:
            if self.existe_username(username):
                raise UsuarioDuplicadoError() from exc
            raise
        return usuario

    def actualizar_estado(self, usuario, *, activo):
        usuario.activo = activo
        usuario.save(update_fields=["activo"])
        return usuario
