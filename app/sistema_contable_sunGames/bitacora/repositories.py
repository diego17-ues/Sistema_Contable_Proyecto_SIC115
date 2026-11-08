from .models import RegistroBitacora


class BitacoraRepository:
    def crear(self, *, accion, resultado, actor=None, afectado=None):
        return RegistroBitacora.objects.create(
            accion=accion, resultado=resultado, actor=actor, afectado=afectado
        )

    def listar(self):
        return RegistroBitacora.objects.select_related(
            "actor", "afectado"
        ).order_by("-fecha_hora", "-id")
