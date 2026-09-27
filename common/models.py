import base36
from django.db import models
from django.conf import settings


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set",
        editable=False
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set",
        editable=False
    )

    class Meta:
        abstract = True


def generate_unique_code(identifier: int, prefix: str):
    if not prefix:
        return None

    mask = {
        '0': '9', '1': 'a', '2': 'j', '3': 'f', '4': 'q', '5': 'k', '6': 'y', '7': '4', '8': 'r', '9': '5', 'a': 'w',
        'b': 'i', 'c': '0', 'd': 'b', 'e': 'z', 'f': '3', 'g': 'e', 'h': 'g', 'i': 'u', 'j': 'l', 'k': 'x', 'l': 'n',
        'm': '8', 'n': '1', 'o': '2', 'p': 'c', 'q': 'd', 'r': 't', 's': 'o', 't': 'v', 'u': 'm', 'v': '6', 'w': '7',
        'x': 'p', 'y': 's', 'z': 'h'
    }
    baseline_number = 100000
    id_36 = base36.dumps(baseline_number + identifier)
    code = ''
    for c in id_36:
        code = code + mask[c]
    
    return prefix.lower() + code

class CodeMixin(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.code:
            return super().save(*args, **kwargs)

        super().save(*args, **kwargs)

        if not self.code and self.pk:
            prefix = getattr(self, 'CLASS_PREFIX', None)
            if prefix:
                unique_code = generate_unique_code(self.pk, prefix)
                if unique_code:
                    self.code = unique_code
                    super().save(update_fields=["code"])
