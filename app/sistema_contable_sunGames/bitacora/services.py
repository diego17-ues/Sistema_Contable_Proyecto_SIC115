class BitacoraService:
    """Registro de eventos de la bitácora (CU-03, solo escritura)."""

    def __init__(self, repositorio):
        self._repositorio = repositorio

    def registrar(self, accion, resultado, *, actor=None, afectado=None):
        return self._repositorio.crear(
            accion=accion, resultado=resultado, actor=actor, afectado=afectado
        )
