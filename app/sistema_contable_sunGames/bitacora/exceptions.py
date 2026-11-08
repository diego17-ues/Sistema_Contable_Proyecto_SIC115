class AuditoriaError(Exception):
    mensaje = "No se pudo completar la operación de auditoría."

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


class SinEventosError(AuditoriaError):
    mensaje = "La bitácora no contiene registros para descargar."


class FormatoNoSoportadoError(AuditoriaError):
    mensaje = "Seleccione un formato de descarga permitido."


class GeneracionArchivoError(AuditoriaError):
    mensaje = "No se pudo generar el archivo; intente nuevamente."
