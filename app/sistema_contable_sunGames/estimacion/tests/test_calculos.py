from decimal import Decimal

from django.test import SimpleTestCase

from estimacion.calculos import (
    costo_hora_pagada,
    costo_mano_obra,
    horas_mensuales,
    pert,
    tarifa_efectiva,
    tarifa_rol,
)


def dec(valor):
    return Decimal(str(valor))


class CalculosTests(SimpleTestCase):
    def test_horas_mensuales(self):
        resultado = horas_mensuales(dec(44), dec(52))
        self.assertAlmostEqual(
            float(resultado), 190.6667, delta=0.0001
        )

    def test_costo_hora_pagada(self):
        horas_mes = horas_mensuales(dec(44), dec(52))
        resultado = costo_hora_pagada(dec(1200), dec("0.246"), horas_mes)
        self.assertAlmostEqual(float(resultado), 7.8420, delta=0.0001)

    def test_tarifa_efectiva_con_eficiencia(self):
        horas_mes = horas_mensuales(dec(44), dec(52))
        pagada = costo_hora_pagada(dec(1200), dec("0.246"), horas_mes)
        resultado = tarifa_efectiva(pagada, dec("0.85"))
        self.assertAlmostEqual(float(resultado), 9.2258, delta=0.0001)

    def test_tarifa_efectiva_con_eficiencia_total(self):
        horas_mes = horas_mensuales(dec(44), dec(52))
        pagada = costo_hora_pagada(dec(1200), dec("0.246"), horas_mes)
        resultado = tarifa_efectiva(pagada, dec("1.00"))
        self.assertAlmostEqual(float(resultado), 7.8420, delta=0.0001)

    def test_pert_valores_exactos(self):
        esperado, sigma = pert(dec(400), dec(500), dec(800))
        self.assertAlmostEqual(float(esperado), 533.3333, delta=0.0001)
        self.assertAlmostEqual(float(sigma), 66.6667, delta=0.0001)

    def test_costo_mano_obra(self):
        tarifa = tarifa_rol(
            dec(1200), dec("0.246"), dec(44), dec(52), dec("0.85")
        )
        esperado, _ = pert(dec(400), dec(500), dec(800))
        costo = costo_mano_obra(esperado, tarifa)
        self.assertAlmostEqual(float(costo), 4920.45, delta=0.05)
