from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from rapidsms_httprouter.urls import urlpatterns as router_urls
from ureport.urls import urlpatterns as ureport_urls
from rapidsms_xforms.urls import urlpatterns as xform_urls
from healthmodels.urls import urlpatterns as healthmodels_urls
from contact.urls import urlpatterns as contact_urls
from django.views.generic.simple import direct_to_template
from generic.views import generic
from generic.sorters import SimpleSorter
from poll.models import Poll
from kenya.views import view_responses
from kenya.utils import get_polls
from ureport.models import MassText
from ureport.forms import AssignToNewPollForm
from contact.forms import FreeSearchForm, DistictFilterForm, MassTextForm
from kenya.forms import FacilityFilterForm, GoLiveForm
from django.contrib.auth.decorators import login_required
from healthmodels.models.HealthProvider import HealthProviderBase
from kenya.sorters import LatestSubmissionSorter
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),

    # RapidSMS core URLs
    (r'^account/', include('rapidsms.urls.login_logout')),
    url(r'^$', direct_to_template, {'template':'kenya/dashboard.html'}, name='rapidsms-dashboard'),
    url('^accounts/login', 'rapidsms.views.login'),
    url('^accounts/logout', 'rapidsms.views.logout'),

    # RapidSMS contrib app URLs
    (r'^ajax/', include('rapidsms.contrib.ajax.urls')),
    (r'^export/', include('rapidsms.contrib.export.urls')),
    (r'^httptester/', include('rapidsms.contrib.httptester.urls')),
    (r'^locations/', include('rapidsms.contrib.locations.urls')),
    (r'^messagelog/', include('rapidsms.contrib.messagelog.urls')),
    (r'^messaging/', include('rapidsms.contrib.messaging.urls')),
    (r'^registration/', include('auth.urls')),
    (r'^scheduler/', include('rapidsms.contrib.scheduler.urls')),
    (r'^polls/', include('poll.urls')),
    (r'^ureport/', include('ureport.urls')),
    # poll management views using generic (rather than built-in poll views
    url(r'^polladmin/$', generic, {
        'model':Poll,
        'queryset':get_polls,
        'objects_per_page':10,
        'selectable':False,
        'partial_row':'kenya/partials/poll_admin_row.html',
        'base_template':'kenya/poll_admin_base.html',
        'results_title':'Polls',
        'sort_column':'start_date',
        'sort_ascending':False,
        'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Question', True, 'question', SimpleSorter(),),
                 ('Start Date', True, 'start_date', SimpleSorter(),),
                 ('Closing Date', True, 'end_date', SimpleSorter()),
                 ('', False, '', None)],
    }, name="kenya-polls"),
    # view responses for a poll (based on generic rather than built-in poll view
    url(r"^(\d+)/responses/$", view_responses, name="kenya-responses"),
   #reporters
    url(r'^reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm, GoLiveForm, AssignToNewPollForm],
      'objects_per_page':25,
      'partial_row':'kenya/partials/reporter_row.html',
      'base_template':'kenya/contacts_base.html',
      'results_title':'Reporters',
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Number', True, 'connection__identity', SimpleSorter(),),
                 ('Role(s)', True, 'groups__name', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Last Reporting Date', True, 'latest_submission_date', LatestSubmissionSorter(),),
                 ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                 ('Facility', True, 'facility__name', SimpleSorter(),),
                 ('Location', True, 'location__name', SimpleSorter(),),
                 ('Active', True, 'active', SimpleSorter(),),
                 ('', False, '', None,)],
    }, name="kenya-contact"),

) + router_urls + xform_urls + healthmodels_urls + contact_urls

if settings.DEBUG:
    urlpatterns += patterns('',
        # helper URLs file that automatically serves the 'static' folder in
        # INSTALLED_APPS via the Django static media server (NOT for use in
        # production)
        (r'^', include('rapidsms.urls.static_media')),
    )

from rapidsms_httprouter.router import get_router
get_router()

