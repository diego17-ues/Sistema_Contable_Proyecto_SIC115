from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from estimacion.models import (
    EstimacionExperto,
    Experto,
    FaseEstimacion,
    Juego,
    ParametroVigente,
    Rol,
    SalarioReferencia,
)


class ValidacionesModelosTests(TestCase):
    def setUp(self):
        self.rol = Rol.objects.create(nombre="Programador", nivel=3)
        self.juego = Juego.objects.create(nombre="Proyecto A")
        self.fase = FaseEstimacion.objects.create(
            juego=self.juego, nombre="Preproducción", orden=1
        )
        self.experto = Experto.objects.create(nombre="Experto Uno")

    def estimacion(self, **campos):
        datos = {
            "juego": self.juego,
            "fase": self.fase,
            "rol": self.rol,
            "experto": self.experto,
            "ronda": 1,
            "optimista": Decimal("400"),
            "moda": Decimal("500"),
            "pesimista": Decimal("800"),
        }
        datos.update(campos)
        return EstimacionExperto.objects.create(**datos)

    def test_estimacion_valida_se_guarda(self):
        estimacion = self.estimacion()
        self.assertEqual(estimacion.optimista, Decimal("400"))

    def test_rechaza_optimista_mayor_que_moda(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.estimacion(optimista=Decimal("600"))

    def test_rechaza_moda_mayor_que_pesimista(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.estimacion(pesimista=Decimal("450"))

    def test_rechaza_horas_negativas(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.estimacion(optimista=Decimal("-1"))

    def test_rechaza_estimacion_duplicada_en_la_ronda(self):
        self.estimacion()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.estimacion()

    def test_salario_rechaza_saldo_negativo(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SalarioReferencia.objects.create(
                    rol=self.rol, salario_bruto=Decimal("-10"),
                    vigente_desde=date(2026, 1, 1),
                )

    def test_salario_rechaza_vigencia_invertida(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SalarioReferencia.objects.create(
                    rol=self.rol, salario_bruto=Decimal("100"),
                    vigente_desde=date(2026, 6, 1),
                    vigente_hasta=date(2026, 1, 1),
                )

    def test_parametro_rechaza_vigencia_invertida(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParametroVigente.objects.create(
                    clave="eficiencia", valor=Decimal("0.85"),
                    vigente_desde=date(2026, 6, 1),
                    vigente_hasta=date(2026, 1, 1),
                )

    def test_parametros_sembrados_tienen_vigencia(self):
        claves = set(
            ParametroVigente.objects.values_list("clave", flat=True)
        )
        self.assertTrue(
            {"horas_semana", "semanas_año", "tasa_cargas_patronales",
             "eficiencia", "umbral_dispersion_delphi"} <= claves
        )
        for parametro in ParametroVigente.objects.all():
            self.assertIsNotNone(parametro.vigente_desde)
