import secrets
from unittest.mock import Mock

from django.test import SimpleTestCase

from bitacora.eventos import Accion, Resultado
from bitacora.services import BitacoraService
from usuarios.exceptions import (
    AreaInicialPendienteError,
    CredencialesInvalidasError,
    CuentaNoHabilitadaError,
    RolNoAutorizadoError,
    ServicioAutenticacionError,
    UsuarioInactivoError,
)
from usuarios.models import Usuario
from usuarios.roles import Rol
from usuarios.services import AccesoService, AutenticacionService

from .fakes import UsuarioRepositoryEnMemoria

CLAVE_CONTADOR = secrets.token_urlsafe(12)
CLAVE_INACTIVO = secrets.token_urlsafe(12)


class AutenticadorFalso:
    """Simula el autenticador con contraseñas en memoria por username."""

    def __init__(self, contrasenas=None, falla_verificar=False,
                 falla_sesion=False):
        self.contrasenas = contrasenas or {}
        self.falla_verificar = falla_verificar
        self.falla_sesion = falla_sesion
        self.sesiones = []

    def verificar_credenciales(self, request, username, password):
        if self.falla_verificar:
            raise ServicioAutenticacionError()
        usuario, contrasena = self.contrasenas.get(username, (None, None))
        if usuario is None or contrasena != password:
            raise CredencialesInvalidasError()
        return usuario

    def abrir_sesion(self, request, usuario):
        if self.falla_sesion:
            raise ServicioAutenticacionError()
        self.sesiones.append(usuario)


class AutenticacionServiceTests(SimpleTestCase):
    def setUp(self):
        self.repositorio = UsuarioRepositoryEnMemoria()
        self.contador = self.repositorio.guardar(Usuario(
            username="contador", nombre_completo="Ana Gómez",
            rol=Rol.CONTADOR_GENERAL,
        ))
        self.inactivo = self.repositorio.guardar(Usuario(
            username="inactivo", nombre_completo="Luis Díaz",
            rol=Rol.CONTADOR_GENERAL, activo=False,
        ))
        self.request = object()
        self.bitacora = Mock(spec=BitacoraService)

    def servicio(self, **kwargs):
        self.autenticador = AutenticadorFalso(
            {
                "contador": (self.contador, CLAVE_CONTADOR),
                "inactivo": (self.inactivo, CLAVE_INACTIVO),
            },
            **kwargs,
        )
        return AutenticacionService(
            self.autenticador, self.repositorio, self.bitacora
        )

    def assert_registrado(self, resultado, actor):
        self.bitacora.registrar.assert_called_once_with(
            Accion.INICIO_SESION, resultado, actor=actor
        )

    def test_credenciales_validas_abren_sesion_y_se_registran(self):
        usuario = self.servicio().iniciar_sesion(
            self.request, "contador", CLAVE_CONTADOR
        )

        self.assertIs(usuario, self.contador)
        self.assertEqual(self.autenticador.sesiones, [self.contador])
        self.assert_registrado(Resultado.EXITOSO, self.contador)

    def test_contrasena_incorrecta_no_abre_sesion_y_se_registra(self):
        with self.assertRaises(CredencialesInvalidasError):
            self.servicio().iniciar_sesion(self.request, "contador", "otra")

        self.assertEqual(self.autenticador.sesiones, [])
        self.assert_registrado(
            Resultado.CREDENCIALES_INCORRECTAS, self.contador
        )

    def test_usuario_inexistente_se_registra_sin_actor(self):
        with self.assertRaises(CredencialesInvalidasError):
            self.servicio().iniciar_sesion(
                self.request, "nadie", CLAVE_CONTADOR
            )

        self.assertEqual(self.autenticador.sesiones, [])
        self.assert_registrado(Resultado.CREDENCIALES_INCORRECTAS, None)

    def test_mensaje_de_credenciales_no_revela_el_dato_fallido(self):
        servicio = self.servicio()
        with self.assertRaises(CredencialesInvalidasError) as usuario_malo:
            servicio.iniciar_sesion(self.request, "nadie", CLAVE_CONTADOR)
        with self.assertRaises(CredencialesInvalidasError) as clave_mala:
            servicio.iniciar_sesion(self.request, "contador", "otra")

        self.assertEqual(
            str(usuario_malo.exception), str(clave_mala.exception)
        )
        self.assertEqual(
            str(clave_mala.exception),
            "Nombre de usuario o contraseña incorrectos.",
        )

    def test_cuenta_inactiva_se_rechaza_y_se_registra(self):
        with self.assertRaises(CuentaNoHabilitadaError) as error:
            self.servicio().iniciar_sesion(
                self.request, "inactivo", CLAVE_INACTIVO
            )

        self.assertEqual(
            str(error.exception),
            "La cuenta no está habilitada para iniciar sesión.",
        )
        self.assertEqual(self.autenticador.sesiones, [])
        self.assert_registrado(Resultado.CUENTA_NO_HABILITADA, self.inactivo)

    def test_falla_al_verificar_no_abre_sesion_y_se_registra(self):
        with self.assertRaises(ServicioAutenticacionError) as error:
            self.servicio(falla_verificar=True).iniciar_sesion(
                self.request, "contador", CLAVE_CONTADOR
            )

        self.assertEqual(
            str(error.exception),
            "No se pudo iniciar sesión; intente nuevamente.",
        )
        self.assertEqual(self.autenticador.sesiones, [])
        self.assert_registrado(Resultado.ERROR_SERVICIO, self.contador)

    def test_falla_al_abrir_sesion_se_informa_y_se_registra(self):
        with self.assertRaises(ServicioAutenticacionError):
            self.servicio(falla_sesion=True).iniciar_sesion(
                self.request, "contador", CLAVE_CONTADOR
            )

        self.assertEqual(self.autenticador.sesiones, [])
        self.assert_registrado(Resultado.ERROR_SERVICIO, self.contador)

    def test_falla_de_bitacora_no_oculta_la_falla_del_servicio(self):
        self.bitacora.registrar.side_effect = RuntimeError("sin base")

        with self.assertRaises(ServicioAutenticacionError):
            self.servicio(falla_verificar=True).iniciar_sesion(
                self.request, "contador", CLAVE_CONTADOR
            )

    def test_intento_con_campo_vacio_se_registra(self):
        self.servicio().registrar_intento_incompleto("contador")

        self.assert_registrado(Resultado.DATOS_INCOMPLETOS, self.contador)

    def test_intento_sin_usuario_se_registra_sin_actor(self):
        self.servicio().registrar_intento_incompleto("")

        self.assert_registrado(Resultado.DATOS_INCOMPLETOS, None)


class AccesoServiceTests(SimpleTestCase):
    def setUp(self):
        self.servicio = AccesoService()
        self.contador = Usuario(
            username="contador", rol=Rol.CONTADOR_GENERAL
        )
        self.admin = Usuario(username="admin", rol=Rol.ADMINISTRADOR)

    def test_area_inicial_del_contador_general(self):
        self.assertEqual(
            self.servicio.area_inicial(self.contador), "dashboard"
        )

    def test_area_inicial_del_administrador_pendiente(self):
        with self.assertRaises(AreaInicialPendienteError):
            self.servicio.area_inicial(self.admin)

    def test_contador_general_accede_a_sus_modulos(self):
        for modulo in ("dashboard", "ledger", "accounts", "reports",
                       "operations"):
            self.servicio.verificar_acceso(self.contador, modulo)

    def test_contador_general_no_accede_a_modulos_de_administrador(self):
        for modulo in ("users", "audit"):
            with self.assertRaises(RolNoAutorizadoError):
                self.servicio.verificar_acceso(self.contador, modulo)

    def test_administrador_sin_modulos_hasta_tener_templates(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.verificar_acceso(self.admin, "dashboard")

    def test_usuario_inactivo_no_accede(self):
        self.contador.activo = False

        with self.assertRaises(UsuarioInactivoError):
            self.servicio.verificar_acceso(self.contador, "dashboard")
