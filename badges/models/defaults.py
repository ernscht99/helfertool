from django.db import models
from django.utils.translation import ugettext_lazy as _


class BadgeDefaults(models.Model):
    role = models.ForeignKey(
        'BadgeRole',
        related_name='+',  # no reverse accessor
        null=True,
        blank=True,
        verbose_name=_("Default role"),
    )

    design = models.ForeignKey(
        'BadgeDesign',
        related_name='+',  # no reverse accessor
        null=True,
        blank=True,
        verbose_name=_("Default design"),
    )