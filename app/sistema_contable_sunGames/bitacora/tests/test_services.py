from unittest.mock import Mock

from django.test import SimpleTestCase

from bitacora.eventos import Accion, Resultado
from bitacora.repositories import BitacoraRepository
from bitacora.services import BitacoraService
from usuarios.models import Usuario
from usuarios.roles import Rol


class BitacoraServiceTests(SimpleTestCase):
    def test_registrar_delega_en_el_repositorio(self):
        repositorio = Mock(spec=BitacoraRepository)
        actor = Usuario(username="admin", rol=Rol.ADMINISTRADOR)
        afectado = Usuario(username="jperez", rol=Rol.CONTADOR_GENERAL)

        registro = BitacoraService(repositorio).registrar(
            Accion.INICIO_SESION, Resultado.EXITOSO,
            actor=actor, afectado=afectado,
        )

        repositorio.crear.assert_called_once_with(
            accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
            actor=actor, afectado=afectado, referencia="",
        )
        self.assertIs(registro, repositorio.crear.return_value)

    def test_actor_y_afectado_son_opcionales(self):
        repositorio = Mock(spec=BitacoraRepository)

        BitacoraService(repositorio).registrar(
            Accion.INICIO_SESION, Resultado.CREDENCIALES_INCORRECTAS
        )

        repositorio.crear.assert_called_once_with(
            accion=Accion.INICIO_SESION,
            resultado=Resultado.CREDENCIALES_INCORRECTAS,
            actor=None, afectado=None, referencia="",
        )
