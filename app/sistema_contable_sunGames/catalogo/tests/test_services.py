import datetime

from django.test import SimpleTestCase

from bitacora.eventos import Accion, Resultado
from catalogo.exceptions import (
    CodigoInmodificableError,
    CodigoNoAsignableError,
    CuentaDuplicadaError,
    DocumentacionIncompletaError,
    GrupoInvalidoError,
    GuardadoCuentaError,
    NaturalezaInvalidaError,
    RubroInvalidoError,
    SinCambiosError,
    SubcuentaNoPermitidaError,
)
from catalogo.models import AprobacionCuenta
from catalogo.services import CatalogoCuentasService, normalizar_denominacion
from usuarios.exceptions import RolNoAutorizadoError, UsuarioInactivoError
from usuarios.roles import Rol
from usuarios.tests.fakes import crear_usuario

from .fakes import (
    ACREEDORA,
    ACTIVO,
    DEUDORA,
    PASIVO,
    BitacoraEnMemoria,
    CuentaRepositoryEnMemoria,
    crear_cuenta,
)

DOCUMENTACION = {
    "justificacion": "Se requiere controlar el efectivo de eventos.",
    "referencia_respaldo": "SOL-2026-014",
    "acuerdo_numero": "JD-07/2026",
    "acuerdo_fecha": datetime.date(2026, 11, 3),
}


def datos(denominacion="Caja de eventos", rubro="1", naturaleza="1",
          **extra):
    return {
        "denominacion": denominacion, "rubro": rubro,
        "naturaleza": naturaleza, "descripcion": "Efectivo de eventos.",
        "reglas_uso": "Solo para eventos.", **DOCUMENTACION, **extra,
    }


class CatalogoTestCase(SimpleTestCase):
    def setUp(self):
        self.admin = crear_usuario("admin")
        self.contador = crear_usuario("cont", Rol.CONTADOR_GENERAL)
        self.bitacora = BitacoraEnMemoria()
        self.preparar()

    def preparar(self, cuentas=(), grupos=((ACTIVO, DEUDORA),)):
        self.repositorio = CuentaRepositoryEnMemoria(cuentas, grupos)
        self.servicio = CatalogoCuentasService(
            self.repositorio, self.bitacora
        )

    def assertSinEscrituras(self, cuentas_esperadas):
        self.assertEqual(len(self.repositorio.cuentas), cuentas_esperadas)
        self.assertEqual(self.repositorio.aprobaciones, [])
        self.assertEqual(self.bitacora.registros, [])


class RegistrarCuentaTest(CatalogoTestCase):
    def test_primer_codigo_del_grupo(self):
        cuenta = self.servicio.registrar(self.admin, datos())

        self.assertEqual(cuenta.codigo, "1101")
        self.assertTrue(cuenta.activa)

    def test_asigna_siguiente_numero_libre_del_grupo(self):
        self.preparar(
            cuentas=[
                crear_cuenta("1101", "Caja general"),
                crear_cuenta("1102", "Caja chica"),
                crear_cuenta("1201", "Mobiliario", naturaleza=ACREEDORA),
                crear_cuenta("2101", "Proveedores", rubro=PASIVO),
            ],
            grupos=[(ACTIVO, DEUDORA), (ACTIVO, ACREEDORA)],
        )

        self.assertEqual(
            self.servicio.registrar(self.admin, datos()).codigo, "1103"
        )
        self.assertEqual(
            self.servicio.registrar(
                self.admin, datos("Equipo", naturaleza="2")
            ).codigo,
            "1202",
        )

    def test_codigo_dado_de_baja_no_se_reutiliza(self):
        self.preparar(cuentas=[
            crear_cuenta("1101", "Caja general"),
            crear_cuenta("1102", "Caja chica", activa=False),
        ])

        cuenta = self.servicio.registrar(self.admin, datos())

        self.assertEqual(cuenta.codigo, "1103")
        self.assertFalse(self.repositorio.cuentas["1102"].activa)

    def test_agotados_los_99_numeros_no_registra(self):
        self.preparar(cuentas=[
            crear_cuenta(f"11{n:02d}", f"Cuenta {n}") for n in range(1, 100)
        ])

        with self.assertRaisesMessage(
            CodigoNoAsignableError, "se usaron los 99 números"
        ):
            self.servicio.registrar(self.admin, datos())
        self.assertSinEscrituras(99)

    def test_registra_alta_en_bitacora_con_su_aprobacion(self):
        cuenta = self.servicio.registrar(self.admin, datos())

        self.assertEqual(self.bitacora.registros, [{
            "accion": Accion.ALTA_CUENTA, "resultado": Resultado.EXITOSO,
            "actor": self.admin, "referencia": "Cuenta 1101",
        }])
        self.assertEqual(self.repositorio.aprobaciones, [{
            "cuenta": cuenta.codigo, "tipo": AprobacionCuenta.Tipo.ALTA,
            "usuario": self.admin, "documentacion": DOCUMENTACION,
            "cambios": [],
        }])

    def test_rechaza_denominacion_equivalente(self):
        self.preparar(cuentas=[crear_cuenta("1101", "Caja de eventos")])

        with self.assertRaises(CuentaDuplicadaError):
            self.servicio.registrar(
                self.admin, datos("  CAJA de  Evéntos ")
            )
        self.assertSinEscrituras(1)

    def test_rechaza_rubro_naturaleza_o_grupo_invalidos(self):
        casos = [
            (datos(rubro="9"), RubroInvalidoError),
            (datos(naturaleza="9"), NaturalezaInvalidaError),
            (datos(rubro="2"), GrupoInvalidoError),
        ]
        for propuesta, error in casos:
            with self.subTest(error=error.__name__):
                with self.assertRaises(error):
                    self.servicio.registrar(self.admin, propuesta)
        self.assertSinEscrituras(0)

    def test_rechaza_sin_acuerdo_de_junta_directiva(self):
        for campo in ("acuerdo_numero", "acuerdo_fecha"):
            with self.subTest(campo=campo):
                with self.assertRaises(DocumentacionIncompletaError) as ctx:
                    self.servicio.registrar(self.admin, datos(**{campo: ""}))
                self.assertEqual(ctx.exception.campo, campo)
        self.assertSinEscrituras(0)

    def test_rechaza_sin_justificacion_ni_respaldo(self):
        for campo in ("justificacion", "referencia_respaldo"):
            with self.subTest(campo=campo):
                with self.assertRaises(DocumentacionIncompletaError):
                    self.servicio.registrar(
                        self.admin, datos(**{campo: "   "})
                    )
        self.assertSinEscrituras(0)

    def test_rechaza_subcuenta(self):
        self.preparar(cuentas=[crear_cuenta("1101", "Caja general")])

        with self.assertRaises(SubcuentaNoPermitidaError):
            self.servicio.registrar(
                self.admin, datos(cuenta_padre="1101")
            )
        self.assertSinEscrituras(1)

    def test_no_acepta_codigo_capturado(self):
        with self.assertRaises(CodigoInmodificableError):
            self.servicio.registrar(self.admin, datos(codigo="1150"))
        self.assertSinEscrituras(0)

    def test_solo_administrador_activo(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.registrar(self.contador, datos())
        with self.assertRaises(UsuarioInactivoError):
            self.servicio.registrar(
                crear_usuario("inact", activo=False), datos()
            )
        self.assertSinEscrituras(0)


class ModificarCuentaTest(CatalogoTestCase):
    def setUp(self):
        super().setUp()
        self.preparar(
            cuentas=[
                crear_cuenta("1101", "Caja general"),
                crear_cuenta("1102", "Caja chica"),
            ],
            grupos=[(ACTIVO, DEUDORA), (PASIVO, ACREEDORA)],
        )
        self.cuenta = self.repositorio.cuentas["1101"]

    def test_codigo_inmodificable_aunque_se_envie(self):
        with self.assertRaises(CodigoInmodificableError):
            self.servicio.modificar(
                self.admin, "1101", datos("Caja central", codigo="1199")
            )
        self.assertEqual(
            self.repositorio.obtener_por_codigo("1101").denominacion,
            "Caja general",
        )
        self.assertNotIn("1199", self.repositorio.cuentas)
        self.assertEqual(self.bitacora.registros, [])

    def test_codigo_actual_enviado_no_bloquea(self):
        revision = self.servicio.modificar(
            self.admin, "1101", datos("Caja central", codigo="1101")
        )

        self.assertEqual(revision.propuesta.codigo, "1101")

    def test_cambio_conserva_codigo_y_guarda_historial(self):
        revision = self.servicio.modificar(
            self.admin, "1101",
            datos("Caja central", rubro="2", naturaleza="2"),
        )

        guardada = self.repositorio.obtener_por_codigo("1101")
        self.assertEqual(guardada.denominacion, "Caja central")
        self.assertEqual(guardada.rubro, PASIVO)
        self.assertEqual(guardada.codigo, "1101")
        self.assertTrue(revision.conserva_codigo)
        aprobacion, = self.repositorio.aprobaciones
        self.assertEqual(
            aprobacion["tipo"], AprobacionCuenta.Tipo.MODIFICACION
        )
        self.assertEqual(aprobacion["usuario"], self.admin)
        cambios = {
            c.campo: (c.anterior, c.nuevo) for c in aprobacion["cambios"]
        }
        self.assertEqual(
            cambios["denominacion"], ("Caja general", "Caja central")
        )
        self.assertEqual(cambios["rubro"], ("1 Activo", "2 Pasivo"))
        self.assertEqual(cambios["naturaleza"], ("1 Deudora", "2 Acreedora"))
        self.assertEqual(self.bitacora.registros, [{
            "accion": Accion.MODIFICACION_CUENTA,
            "resultado": Resultado.EXITOSO, "actor": self.admin,
            "referencia": "Cuenta 1101",
        }])

    def test_revisar_no_guarda(self):
        revision = self.servicio.revisar(
            self.admin, "1101", datos("Caja central")
        )

        self.assertFalse(revision.conserva_codigo)
        self.assertEqual(self.cuenta.denominacion, "Caja general")
        self.assertEqual(self.repositorio.aprobaciones, [])
        self.assertEqual(self.bitacora.registros, [])

    def test_rechaza_sin_acuerdo_de_junta_directiva(self):
        with self.assertRaises(DocumentacionIncompletaError) as ctx:
            self.servicio.modificar(
                self.admin, "1101", datos("Caja central", acuerdo_numero="")
            )

        self.assertEqual(ctx.exception.campo, "acuerdo_numero")
        self.assertEqual(self.cuenta.denominacion, "Caja general")
        self.assertEqual(self.bitacora.registros, [])

    def test_falla_al_guardar_conserva_valores_anteriores(self):
        self.repositorio.falla_al_guardar = True

        with self.assertRaises(GuardadoCuentaError):
            self.servicio.modificar(
                self.admin, "1101", datos("Caja central", rubro="2",
                                          naturaleza="2")
            )
        guardada = self.repositorio.obtener_por_codigo("1101")
        self.assertEqual(guardada.denominacion, "Caja general")
        self.assertEqual(guardada.rubro, ACTIVO)
        self.assertEqual(self.bitacora.registros, [])

    def test_denominacion_de_otra_cuenta_es_duplicada(self):
        with self.assertRaises(CuentaDuplicadaError):
            self.servicio.modificar(self.admin, "1101", datos("caja chica"))

    def test_sin_cambios(self):
        propuesta = datos("Caja general")
        propuesta.update(descripcion="Descripción", reglas_uso="Reglas")

        with self.assertRaises(SinCambiosError):
            self.servicio.modificar(self.admin, "1101", propuesta)

    def test_rechaza_subcuenta(self):
        with self.assertRaises(SubcuentaNoPermitidaError):
            self.servicio.modificar(
                self.admin, "1101", datos("Caja central", cuenta_padre="1102")
            )

    def test_contador_no_modifica(self):
        with self.assertRaises(RolNoAutorizadoError):
            self.servicio.modificar(self.contador, "1101", datos("Otra"))
        self.assertEqual(self.cuenta.denominacion, "Caja general")


class ConsultaCatalogoTest(CatalogoTestCase):
    def setUp(self):
        super().setUp()
        self.preparar(cuentas=[
            crear_cuenta("1101", "Caja general"),
            crear_cuenta("1102", "Caja chica", activa=False),
        ])

    def test_contador_y_administrador_consultan(self):
        for actor in (self.admin, self.contador):
            with self.subTest(actor=actor.username):
                self.assertEqual(len(self.servicio.listar(actor)), 2)
                self.assertEqual(
                    self.servicio.obtener(actor, "1102").denominacion,
                    "Caja chica",
                )

    def test_filtros(self):
        cuentas = self.servicio.listar(self.contador, activa=False)

        self.assertEqual([c.codigo for c in cuentas], ["1102"])

    def test_usuario_inactivo_no_consulta(self):
        with self.assertRaises(UsuarioInactivoError):
            self.servicio.listar(
                crear_usuario("inact", Rol.CONTADOR_GENERAL, activo=False)
            )

    def test_solo_el_administrador_puede_modificar(self):
        self.assertTrue(self.servicio.puede_modificar(self.admin))
        self.assertFalse(self.servicio.puede_modificar(self.contador))


class NormalizarDenominacionTest(SimpleTestCase):
    def test_ignora_mayusculas_tildes_y_espacios(self):
        self.assertEqual(
            normalizar_denominacion("  Depreciación   ACUMULADA "),
            "depreciacion acumulada",
        )
