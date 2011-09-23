from django.db import models
from rapidsms.contrib.locations.models import Location, Point
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


class HealthFacilityType(models.Model):

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=30, unique=True)

    def __unicode__(self):
        return self.name


class HealthFacility(models.Model):

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True, null=False)
    type = models.ForeignKey(HealthFacilityType, blank=True, null=True)
    # Catchment areas should be locations that makes sense independently, i.e.
    # a city, town, village, parish, region, district, etc.
    catchment_areas = models.ManyToManyField(Location, null=True, blank=True)
    # location is the physical location of the health facility itself.
    # This location should only represent the facility's location, and
    # shouldn't be overloaded to also represent the location of a town
    # or village.  Depending on pending changes to the locations model,
    # this could eventually be a ForeignKey to the Point class instead.
    location = models.ForeignKey(Point, null=True, blank=True)
    # report_to generic relation.
    report_to_type = models.ForeignKey(ContentType, null=True, blank=True)
    report_to_id = models.PositiveIntegerField(null=True, blank=True)
    report_to = generic.GenericForeignKey('report_to_type', 'report_to_id')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        ''' generates a code if none provided '''
        if not self.code:
            # generation is dumb now and not conflict-safe
            # probably suffiscient to handle human entry through django-admin
            chars = '1234567890_QWERTYUOPASDFGHJKLZXCVBNM'
            self.code = u"gen" + u"".join([choice(chars) \
                                          for i in range(10)]).lower()

