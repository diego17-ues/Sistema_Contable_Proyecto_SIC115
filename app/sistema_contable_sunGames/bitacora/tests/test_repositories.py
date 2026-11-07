from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from bitacora.eventos import Accion, Resultado
from bitacora.models import RegistroBitacora
from bitacora.repositories import BitacoraRepository
from usuarios.models import Usuario
from usuarios.roles import Rol


class BitacoraRepositoryTests(TestCase):
    def setUp(self):
        self.repositorio = BitacoraRepository()
        self.usuario = Usuario.objects.create(
            username="jperez", nombre_completo="Juan Pérez",
            rol=Rol.CONTADOR_GENERAL,
        )

    def test_crear_guarda_fecha_hora_actor_accion_y_resultado(self):
        registro = self.repositorio.crear(
            accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
            actor=self.usuario,
        )

        guardado = RegistroBitacora.objects.get(pk=registro.pk)
        self.assertIsNotNone(guardado.fecha_hora)
        self.assertEqual(guardado.actor, self.usuario)
        self.assertIsNone(guardado.afectado)
        self.assertEqual(guardado.accion, Accion.INICIO_SESION)
        self.assertEqual(guardado.resultado, Resultado.EXITOSO)

    def test_crear_admite_usuario_afectado(self):
        afectado = Usuario.objects.create(
            username="mlopez", nombre_completo="María López",
            rol=Rol.CONTADOR_GENERAL,
        )

        registro = self.repositorio.crear(
            accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
            actor=self.usuario, afectado=afectado,
        )

        self.assertEqual(
            RegistroBitacora.objects.get(pk=registro.pk).afectado, afectado
        )

    def test_crear_sin_actor(self):
        registro = self.repositorio.crear(
            accion=Accion.INICIO_SESION,
            resultado=Resultado.CREDENCIALES_INCORRECTAS,
        )

        self.assertIsNone(RegistroBitacora.objects.get(pk=registro.pk).actor)

    def test_la_base_rechaza_resultados_no_definidos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RegistroBitacora.objects.create(
                accion=Accion.INICIO_SESION, resultado="OTRO"
            )

    def test_un_usuario_con_historial_no_se_puede_borrar(self):
        self.repositorio.crear(
            accion=Accion.INICIO_SESION, resultado=Resultado.EXITOSO,
            actor=self.usuario,
        )

        with self.assertRaises(ProtectedError):
            self.usuario.delete()
