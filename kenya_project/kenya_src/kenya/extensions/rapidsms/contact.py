from django.db import models

from kenya.schools.models import School
from healthmodels.models.HealthFacility import HealthFacility

class ActivatedContact(models.Model):
    """
    This extension for Contacts allows developers to tie a Contact to
    the Location object they're reporting from.
    """
    active = models.BooleanField(default=False)
    school = models.ForeignKey(School, null=True)
    health_facility = models.ForeignKey(HealthFacility, null=True)

    class Meta:
        abstract = True
