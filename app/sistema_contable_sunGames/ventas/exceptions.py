class VentasError(Exception):
    mensaje = "No se pudo completar la operación de ventas."

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


class EventoInvalidoError(VentasError):
    mensaje = "El evento de venta no es válido."


class MonedaNoAdmitidaError(EventoInvalidoError):
    mensaje = "La moneda del evento no está admitida."


class VentaDuplicadaError(EventoInvalidoError):
    mensaje = "Ya se recibió una venta con ese identificador."


class VentaNoEncontradaError(VentasError):
    mensaje = "La venta no existe."


class VentaYaRegistradaError(VentasError):
    mensaje = "La venta ya está registrada en el Libro Mayor."


class ContabilizacionError(VentasError):
    mensaje = "No se pudo registrar la venta en el Libro Mayor."
