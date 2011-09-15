from generic.forms import FilterForm, ActionForm
from healthmodels.models import HealthFacility
from django import forms
from rapidsms.contrib.locations.models import Location


class LocationFilterForm(FilterForm):

    """ filter cvs districs on their districts """

    camp = forms.ChoiceField(choices=(('', '-----'), (-1,
                                 'No Camp')) + tuple([(int(d.pk),
                                 d.name) for d in
                                 Location.objects.filter(type__slug='camp'
                                 ).order_by('name')]))

    def filter(self, request, queryset):
        camp_pk = self.cleaned_data['camp']
        if camp_pk == '':
            return queryset
        elif int(camp_pk) == -1:
            return queryset.filter(reporting_location=None)
        else:

            try:
                camp = Location.objects.get(pk=camp_pk)
            except Location.DoesNotExist:
                camp = None
            if camp:
                return queryset.filter(reporting_location__in=camp.get_descendants(include_self=True))
            else:
                return queryset


class FacilityFilterForm(FilterForm):
    """ filter form for health facilities """
    facility = forms.ChoiceField(choices=(('', '-----'), (-1, 'Has No Facility'),) + tuple(HealthFacility.objects.values_list('pk', 'name').order_by('type', 'name')))


    def filter(self, request, queryset):
        facility_pk = self.cleaned_data['facility']
        if facility_pk == '':
            return queryset
        elif int(facility_pk) == -1:
            return queryset.filter(facility=None)
        else:
            return queryset.filter(facility=facility_pk)


class GoLiveForm(ActionForm):

    action_label = 'Activate Selected Users'

    def perform(self, request, results):
        if results is None or len(results) == 0:
            return ('Select at least one reporter!', 'error')

        results.update(active=True)
        return ('The %d selected reporters are now live for sending in reports' % len(results), 'success',)

