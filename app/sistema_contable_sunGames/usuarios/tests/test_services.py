from unittest.mock import Mock

from django.test import SimpleTestCase

from bitacora.eventos import Accion, Resultado
from usuarios.exceptions import (
    RolInvalidoError,
    RolNoAutorizadoError,
    UsuarioDuplicadoError,
    UsuarioInactivoError,
    UsuarioNoEncontradoError,
)
from usuarios.repositories import UsuarioRepository
from usuarios.roles import Rol
from usuarios.services import UsuarioService

from .fakes import (
    CLAVE_NUEVA,
    BitacoraEnMemoria,
    UsuarioRepositoryEnMemoria,
    crear_usuario,
)


class BaseServicioTest(SimpleTestCase):
    def setUp(self):
        self.admin = crear_usuario("admin")
        self.repositorio = UsuarioRepositoryEnMemoria([self.admin])
        self.servicio = UsuarioService(self.repositorio, BitacoraEnMemoria())


class AgregarUsuarioTest(BaseServicioTest):
    """CU-02.1 Agregar Usuario."""

    def test_registra_usuario_activo_con_rol(self):
        usuario = self.servicio.agregar(
            self.admin,
            username="jperez",
            nombre_completo="Juan Pérez",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        self.assertEqual(usuario.username, "jperez")
        self.assertEqual(usuario.nombre_completo, "Juan Pérez")
        self.assertEqual(usuario.rol, Rol.CONTADOR_GENERAL)
        self.assertTrue(usuario.activo)
        self.assertTrue(self.repositorio.existe_username("jperez"))

    def test_cuenta_nueva_con_la_contrasena_asignada(self):
        usuario = self.servicio.agregar(
            self.admin,
            username="jperez",
            nombre_completo="Juan Pérez",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        self.assertTrue(usuario.check_password(CLAVE_NUEVA))
        self.assertNotEqual(usuario.password, CLAVE_NUEVA)

    def test_rechaza_username_duplicado(self):
        self.servicio.agregar(
            self.admin, username="jperez", nombre_completo="Juan",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        with self.assertRaises(UsuarioDuplicadoError):
            self.servicio.agregar(
                self.admin, username="jperez", nombre_completo="Otro",
                contrasena=CLAVE_NUEVA, rol=Rol.ADMINISTRADOR,
            )

    def test_rechaza_rol_no_valido(self):
        for rol in ("CONTADOR_COSTOS", "", "SUPERUSUARIO"):
            with self.subTest(rol=rol), self.assertRaises(RolInvalidoError):
                self.servicio.agregar(
                    self.admin, username="jperez", nombre_completo="Juan",
                    contrasena=CLAVE_NUEVA, rol=rol,
                )
        self.assertFalse(self.repositorio.existe_username("jperez"))

    def test_actor_sin_rol_administrador_no_puede_agregar(self):
        contador = crear_usuario("conta", rol=Rol.CONTADOR_GENERAL)

        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.agregar(
                contador, username="jperez", nombre_completo="Juan",
                contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
            )
        self.assertFalse(self.repositorio.existe_username("jperez"))

    def test_actor_inactivo_no_puede_agregar(self):
        admin_inactivo = crear_usuario("admin2", activo=False)

        with self.assertRaises(UsuarioInactivoError):
            self.servicio.agregar(
                admin_inactivo, username="jperez", nombre_completo="Juan",
                contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
            )

    def test_no_llama_a_crear_si_el_username_existe(self):
        repositorio = Mock(spec=UsuarioRepository)
        repositorio.existe_username.return_value = True
        servicio = UsuarioService(repositorio, BitacoraEnMemoria())

        with self.assertRaises(UsuarioDuplicadoError):
            servicio.agregar(
                self.admin, username="jperez", nombre_completo="Juan",
                contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
            )
        repositorio.existe_username.assert_called_once_with("jperez")
        repositorio.guardar.assert_not_called()

    def test_asigna_la_contrasena_antes_de_guardar(self):
        repositorio = Mock(spec=UsuarioRepository)
        repositorio.existe_username.return_value = False
        usuario = repositorio.nuevo.return_value
        usuario.set_password.side_effect = (
            lambda _: repositorio.guardar.assert_not_called()
        )
        servicio = UsuarioService(repositorio, BitacoraEnMemoria())

        resultado = servicio.agregar(
            self.admin, username="jperez", nombre_completo="Juan",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        repositorio.nuevo.assert_called_once_with(
            username="jperez", nombre_completo="Juan",
            rol=Rol.CONTADOR_GENERAL,
        )
        usuario.set_password.assert_called_once_with(CLAVE_NUEVA)
        repositorio.guardar.assert_called_once_with(usuario)
        self.assertIs(resultado, repositorio.guardar.return_value)


class DesactivarUsuarioTest(BaseServicioTest):
    """CU-02.2 Desactivar Usuario."""

    def setUp(self):
        super().setUp()
        self.objetivo = crear_usuario("jperez", rol=Rol.CONTADOR_GENERAL)
        self.repositorio = UsuarioRepositoryEnMemoria(
            [self.admin, self.objetivo]
        )
        self.servicio = UsuarioService(self.repositorio, BitacoraEnMemoria())

    def test_desactiva_sin_borrar_el_registro(self):
        usuario = self.servicio.desactivar(self.admin, "jperez")

        self.assertFalse(usuario.activo)
        conservado = self.repositorio.obtener_por_username("jperez")
        self.assertFalse(conservado.activo)
        self.assertEqual(conservado.nombre_completo, "Nombre jperez")
        self.assertEqual(conservado.rol, Rol.CONTADOR_GENERAL)

    def test_usuario_ya_inactivo_informa_la_causa(self):
        self.servicio.desactivar(self.admin, "jperez")

        with self.assertRaisesMessage(
            UsuarioInactivoError, "El usuario ya está inactivo."
        ):
            self.servicio.desactivar(self.admin, "jperez")

    def test_usuario_inexistente(self):
        with self.assertRaises(UsuarioNoEncontradoError):
            self.servicio.desactivar(self.admin, "noexiste")

    def test_actor_sin_rol_administrador_no_puede_desactivar(self):
        contador = crear_usuario("conta", rol=Rol.CONTADOR_GENERAL)

        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.desactivar(contador, "jperez")
        self.assertTrue(self.objetivo.activo)

    def test_actor_inactivo_no_puede_desactivar(self):
        admin_inactivo = crear_usuario("admin2", activo=False)

        with self.assertRaises(UsuarioInactivoError):
            self.servicio.desactivar(admin_inactivo, "jperez")
        self.assertTrue(self.objetivo.activo)

    def test_no_actualiza_estado_si_ya_esta_inactivo(self):
        repositorio = Mock(spec=UsuarioRepository)
        repositorio.obtener_por_username.return_value = crear_usuario(
            "jperez", activo=False
        )
        servicio = UsuarioService(repositorio, BitacoraEnMemoria())

        with self.assertRaises(UsuarioInactivoError):
            servicio.desactivar(self.admin, "jperez")
        repositorio.actualizar_estado.assert_not_called()


class ListarUsuariosTest(BaseServicioTest):
    """CU-02.3 Consultar Usuarios / CU-02 listado."""

    def test_lista_usuarios_registrados(self):
        self.servicio.agregar(
            self.admin, username="jperez", nombre_completo="Juan",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        usernames = [u.username for u in self.servicio.listar(self.admin)]

        self.assertEqual(usernames, ["admin", "jperez"])

    def test_sin_usuarios_devuelve_listado_vacio(self):
        servicio = UsuarioService(
            UsuarioRepositoryEnMemoria(), BitacoraEnMemoria()
        )

        self.assertEqual(list(servicio.listar(self.admin)), [])

    def test_actor_sin_rol_administrador_no_puede_consultar(self):
        contador = crear_usuario("conta", rol=Rol.CONTADOR_GENERAL)

        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.listar(contador)


class BitacoraDeUsuariosTest(SimpleTestCase):
    """CU-02.1 y CU-02.2: los cambios se registran en la bitácora."""

    def setUp(self):
        self.admin = crear_usuario("admin")
        self.bitacora = BitacoraEnMemoria()
        self.repositorio = UsuarioRepositoryEnMemoria([self.admin])
        self.servicio = UsuarioService(self.repositorio, self.bitacora)

    def test_alta_con_contrasena_asignada_y_registrada(self):
        usuario = self.servicio.agregar(
            self.admin, username="nuevo", nombre_completo="Nuevo",
            contrasena=CLAVE_NUEVA, rol=Rol.CONTADOR_GENERAL,
        )

        self.assertTrue(usuario.check_password(CLAVE_NUEVA))
        self.assertTrue(usuario.activo)
        self.assertEqual(self.bitacora.registros, [{
            "accion": Accion.ALTA_USUARIO, "resultado": Resultado.EXITOSO,
            "actor": self.admin, "afectado": usuario,
        }])

    def test_alta_rechazada_no_se_registra(self):
        with self.assertRaises(UsuarioDuplicadoError):
            self.servicio.agregar(
                self.admin, username="admin", nombre_completo="Otro",
                contrasena=CLAVE_NUEVA, rol=Rol.ADMINISTRADOR,
            )
        self.assertEqual(self.bitacora.registros, [])

    def test_desactivacion_registrada_sin_borrar(self):
        contador = crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.repositorio.guardar(contador)

        self.servicio.desactivar(self.admin, "cont")

        self.assertFalse(contador.activo)
        self.assertIn(contador, self.repositorio.listar())
        self.assertEqual(self.bitacora.registros, [{
            "accion": Accion.DESACTIVACION_USUARIO,
            "resultado": Resultado.EXITOSO,
            "actor": self.admin, "afectado": contador,
        }])

    def test_desactivar_cuenta_ya_inactiva_informa_la_causa(self):
        self.repositorio.guardar(
            crear_usuario("inact", Rol.CONTADOR_GENERAL, activo=False)
        )

        with self.assertRaisesMessage(
            UsuarioInactivoError, "El usuario ya está inactivo."
        ):
            self.servicio.desactivar(self.admin, "inact")
        self.assertEqual(self.bitacora.registros, [])

    def test_consulta_no_modifica_ni_registra(self):
        ficha = self.servicio.obtener(self.admin, "admin")

        self.assertIs(ficha, self.admin)
        self.assertEqual(self.bitacora.registros, [])

    def test_consulta_exige_administrador(self):
        contador = crear_usuario("cont", Rol.CONTADOR_GENERAL)

        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.obtener(contador, "admin")
