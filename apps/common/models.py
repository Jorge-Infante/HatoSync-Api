from django.db import models


class DeferredFilesMixin(models.Model):
    """
    Pospone el guardado de archivos al crear un registro, para que los
    `upload_to` que usan `instance.pk` ya tengan el ID asignado.

    El modelo debe listar sus campos de archivo en `DEFERRED_FILE_FIELDS`.
    """

    DEFERRED_FILE_FIELDS = ()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is None:
            deferred = {}
            for field_name in self.DEFERRED_FILE_FIELDS:
                file = getattr(self, field_name)
                if file:
                    deferred[field_name] = file
                    setattr(self, field_name, None)
            super().save(*args, **kwargs)
            if deferred:
                for field_name, file in deferred.items():
                    setattr(self, field_name, file)
                super().save(update_fields=list(deferred.keys()))
            return
        super().save(*args, **kwargs)
