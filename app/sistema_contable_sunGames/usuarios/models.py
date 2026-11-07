from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from .roles import Rol

USERNAME_MAX_LENGTH = 8
NOMBRE_COMPLETO_MAX_LENGTH = 150


class Usuario(AbstractBaseUser):
    username = models.CharField(
        "nombre de usuario", max_length=USERNAME_MAX_LENGTH, unique=True
    )
    nombre_completo = models.CharField(
        "nombre completo", max_length=NOMBRE_COMPLETO_MAX_LENGTH
    )
    rol = models.CharField("rol", max_length=20, choices=Rol.choices)
    activo = models.BooleanField("activo", default=True)
    fecha_creacion = models.DateTimeField(
        "fecha de creación", auto_now_add=True
    )

    objects = BaseUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["nombre_completo", "rol"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rol__in=Rol.values),
                name="usuario_rol_valido",
            ),
            models.CheckConstraint(
                check=~models.Q(username=""),
                name="usuario_username_no_vacio",
            ),
            models.CheckConstraint(
                check=~models.Q(nombre_completo=""),
                name="usuario_nombre_completo_no_vacio",
            ),
        ]

    @property
    def is_active(self):
        return self.activo

    def __str__(self):
        return self.username
