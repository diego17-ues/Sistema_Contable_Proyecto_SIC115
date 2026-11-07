from django.db import DataError, IntegrityError, transaction
from django.test import TestCase

from usuarios.composition import crear_usuario_service
from usuarios.exceptions import UsuarioDuplicadoError, UsuarioNoEncontradoError
from usuarios.models import Usuario
from usuarios.repositories import UsuarioRepository
from usuarios.roles import Rol


class UsuarioRepositoryTest(TestCase):
    """Integración contra PostgreSQL."""

    def setUp(self):
        self.repositorio = UsuarioRepository()

    def crear(self, username="jperez", rol=Rol.CONTADOR_GENERAL):
        return self.repositorio.guardar(
            self.repositorio.nuevo(
                username=username, nombre_completo="Juan Pérez", rol=rol
            )
        )

    def test_guardar_registra_usuario_activo(self):
        usuario = self.crear()

        guardado = Usuario.objects.get(pk=usuario.pk)
        self.assertTrue(guardado.activo)
        self.assertTrue(guardado.is_active)
        self.assertEqual(guardado.rol, Rol.CONTADOR_GENERAL)

    def test_username_unico_en_base_de_datos(self):
        self.crear()

        with self.assertRaises(UsuarioDuplicadoError):
            self.crear()
        self.assertEqual(Usuario.objects.filter(username="jperez").count(), 1)

    def test_username_maximo_ocho_caracteres_en_base_de_datos(self):
        self.crear(username="a" * 8)

        with self.assertRaises(DataError), transaction.atomic():
            self.crear(username="a" * 9)

    def test_rol_fuera_de_catalogo_viola_restriccion(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear(rol="CONTADOR_COSTOS")

    def test_existe_username(self):
        self.crear()

        self.assertTrue(self.repositorio.existe_username("jperez"))
        self.assertFalse(self.repositorio.existe_username("otro"))

    def test_obtener_por_username_inexistente(self):
        with self.assertRaises(UsuarioNoEncontradoError):
            self.repositorio.obtener_por_username("noexiste")

    def test_actualizar_estado_conserva_el_registro(self):
        usuario = self.crear()

        self.repositorio.actualizar_estado(usuario, activo=False)

        guardado = Usuario.objects.get(pk=usuario.pk)
        self.assertFalse(guardado.activo)
        self.assertFalse(guardado.is_active)
        self.assertEqual(guardado.nombre_completo, "Juan Pérez")

    def test_listar_ordenado_por_username(self):
        self.crear("zeta")
        self.crear("alfa")

        self.assertEqual(
            [u.username for u in self.repositorio.listar()], ["alfa", "zeta"]
        )


class UsuarioServiceIntegracionTest(TestCase):
    """CU-02.1 y CU-02.2 con el repositorio real."""

    def setUp(self):
        repositorio = UsuarioRepository()
        self.admin = repositorio.guardar(
            repositorio.nuevo(
                username="admin", nombre_completo="Administrador",
                rol=Rol.ADMINISTRADOR,
            )
        )
        self.servicio = crear_usuario_service()

    def test_alta_y_desactivacion_no_borran_el_registro(self):
        self.servicio.agregar(
            self.admin, username="jperez", nombre_completo="Juan Pérez",
            rol=Rol.CONTADOR_GENERAL,
        )
        total = Usuario.objects.count()

        self.servicio.desactivar(self.admin, "jperez")

        self.assertEqual(Usuario.objects.count(), total)
        guardado = Usuario.objects.get(username="jperez")
        self.assertFalse(guardado.activo)
        self.assertFalse(guardado.has_usable_password())

    def test_alta_duplicada_no_crea_otra_cuenta(self):
        self.servicio.agregar(
            self.admin, username="jperez", nombre_completo="Juan Pérez",
            rol=Rol.CONTADOR_GENERAL,
        )

        with self.assertRaises(UsuarioDuplicadoError):
            self.servicio.agregar(
                self.admin, username="jperez", nombre_completo="Otro",
                rol=Rol.ADMINISTRADOR,
            )
        self.assertEqual(Usuario.objects.filter(username="jperez").count(), 1)
