from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from rapidsms_xforms.models import XForm, XFormField, XFormFieldConstraint, XFormSubmission
from script.models import Script, ScriptStep, ScriptSession
from script.utils.handling import find_closest_match, find_best_response
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from django.db.models import Count
from healthmodels.models import HealthProvider
import datetime
from rapidsms_httprouter.models import Message
from ureport.models import MassText
from kenya.schools.models import School
from healthmodels.models import HealthFacility

def get_messages(**kwargs):
    return Message.objects.filter(direction='I')

def get_mass_messages(**kwargs):
    return [(p.question, p.start_date, p.user.username, p.contacts.count(), 'Poll Message') for p in Poll.objects.exclude(start_date=None)] + [(m.text, m.date, m.user.username, m.contacts.count(), 'Mass Text') for m in MassText.objects.all()]


XFORMS = (
    ('', 'epi', ',;:*.\\s"', 'Epi Report', 'Weekly-submitted epidemiological reports'),
    ('', 'nut', ',;:*.\\s"', 'Nutrition Report', 'Weekly-submitted nutritional reports'),
    ('', 'cfp', ',;:*.\\s"', 'Child Friendly Schools Report', 'Weekly-submitted school reports'),
    ('', 'child', ',;:*.\\s"', 'Child Protection Sites Report', 'Weekly-submitted protection reports'),
)


XFORM_FIELDS = {
    'epi':[
        ('dairrhea', 'int', 'acute water diarrhea cases', True),
        ('measles', 'int', 'suspected measels cases', True),
        ('lrti', 'int', 'LRTI/ARI cases', True),
    ],
    'nut':[
        ('sam', 'int', 'SAM', True),
        ('mam', 'int', 'MAM', True),
        ('recover', 'int', 'recovered', True),
        ('death', 'int', 'deaths', True),
    ],
    'cfp':[
        ('bvisits', 'int', 'boys visits', True),
        ('gvisits', 'int', 'girls visits', True),
    ],
    'child':[
        ('bvisits', 'int', 'boys visits', True),
        ('gvisits', 'int', 'girls visits', True),
    ],
}

def init_xforms():
    init_xforms_from_tuples(XFORMS, XFORM_FIELDS)

def init_xforms_from_tuples(xforms, xform_fields):
    user = User.objects.get(username='admin')
    xform_dict = {}
    for keyword_prefix, keyword, separator, name, description in xforms:
        xform, created = XForm.objects.get_or_create(
            keyword=keyword,
            keyword_prefix=keyword_prefix,
            defaults={
                'name':name,
                'description':description,
                'response':'',
                'active':True,
                'owner':user,
                'separator':separator,
                'command_prefix':'',
                'site':Site.objects.get_current()
            }
        )
        xform_dict["%s%s" % (keyword_prefix, keyword)] = xform

    for form_key, attributes in xform_fields.items():
        order = 0
        form = xform_dict[form_key]
        for command, field_type, description, required in attributes:
            xformfield, created = XFormField.objects.get_or_create(
                command=command,
                xform=form,
                defaults={
                    'order':order,
                    'field_type':field_type,
                    'type':field_type,
                    'name':description,
                    'description':description,
                }
            )
            if required:
                xformfieldconstraint, created = XFormFieldConstraint.objects.get_or_create(
                    field=xformfield,
                    defaults={
                        'type':'req_val',
                         'message':("Expected %s, none provided." % description)
                    }
            )
            order = order + 1
    return xform_dict


def check_basic_validity(xform_type, submission, health_provider, day_range):
    xform = XForm.objects.get(keyword=xform_type)
    start_date = datetime.datetime.now() - datetime.timedelta(hours=(day_range * 24))
    XFormSubmission.objects.filter(connection__contact__healthproviderbase__healthprovider=health_provider, \
                                            xform=xform, \
                                            created__gte=start_date)\
                           .exclude(pk=submission.pk)\
                           .update(has_errors=True)



def xform_received_handler(sender, **kwargs):
    xform = kwargs['xform']
    submission = kwargs['submission']

    if submission.has_errors:
        submission.response = "Thank you for contacting us. If this was a routine weekly/monthly report, please check your form and resubmit. All other messages will be reviewed and responded to as appropriate."
        submission.save()
        return

    # TODO: check validity
    kwargs.setdefault('message', None)
    message = kwargs['message']
    try:
        message = message.db_message
        if not message:
            return
    except AttributeError:
        return

    try:
        health_provider = submission.connection.contact.healthproviderbase.healthprovider
    except:
        submission.response = "Please first register with the system by texting in 'join'."
        submission.has_errors = True
        submission.save()
        return

    if xform.keyword in [i[1] for i in XFORMS]:
        check_basic_validity(xform.keyword, submission, health_provider, 1)
        value_list = []
        for v in submission.eav.get_values():
            value_list.append("%s %d" % (v.attribute.name, v.value_int))
        value_list[len(value_list) - 1] = " and %s" % value_list[len(value_list) - 1]
        submission.response = "You reported %s.If there is an error,please resend." % ','.join(value_list)

        if not (submission.connection.contact and submission.connection.contact.active):
            submission.has_errors = True

        submission.save()


def init_autoreg(sender, **kwargs):
    script, created = Script.objects.get_or_create(
            slug="autoreg", defaults={
            'name':"Default autoregistration script"})
    if created:
        user, created = User.objects.get_or_create(username="admin")
        script.sites.add(Site.objects.get_current())
        name_poll = Poll.objects.create(\
            name='autoreg_name', \
            user=user, type=Poll.TYPE_TEXT, \
            question="Thank you for registering for UNICEF Kenya's data collection system. We are going to ask you a few questions.  What is your name?", \
            default_response=''
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=name_poll,
            order=0,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        org_poll = Poll.objects.create(\
            name='autoreg_org', \
            user=user, type=Poll.TYPE_TEXT, \
            question="What organization do you work for?", \
            default_response=''
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=org_poll,
            order=1,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))

        field_poll = Poll.objects.create(\
            name='autoreg_field', \
            user=user, type=Poll.TYPE_TEXT, \
            question="What field do you work in?", \
            default_response=''
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=field_poll,
            order=2,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))

        division_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='autoreg_division',
            question='What division do you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=division_poll,
            order=3,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        building_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='autoreg_building',
            question='What is the name of the facility or school you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=building_poll,
            order=4,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome to the UNICEF Kenya data collection system. You are now a fully registered member. Your timely reports are very import to us!",
            order=5,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=60,
            giveup_offset=0,
        ))
        for poll in [name_poll, org_poll, field_poll, camp_poll]:
            poll.sites.add(Site.objects.get_current())

def init_groups():
    for g in ['UNICEF', 'UNHCR', 'NGO', 'Government', 'Other Organizations', 'Health', 'Education', 'Child Protection', 'WASH', 'Water and Sanitation', 'Other Fields']:
        Group.objects.get_or_create(name=g)

models_created = []
structures_initialized = False

def init_structures(sender, **kwargs):
    global models_created
    global structures_initialized
    models_created.append(sender.__name__)
    required_models = ['eav.models', 'rapidsms_xforms.models', 'poll.models', 'script.models', 'django.contrib.auth.models']

    for required in required_models:
        if required not in models_created:
            return
    if not structures_initialized:
        init_groups()
        init_xforms()
        init_autoreg(sender)
        structures_initialized = True


def do_autoreg(**kwargs):
    ''' 
    Kenya autoreg post registration particulars handling. 
    This method responds to a signal sent by the Script module on completion of the cvs_autoreg script
    '''
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'autoreg':
        return
    session = ScriptSession.objects.filter(script=progress.script, connection=connection).order_by('-end_time')[0]
    script = progress.script

    contact = connection.contact.healthproviderbase.healthprovider if connection.contact else HealthProvider.objects.create()
    connection.contact = contact
    connection.save()

    name_poll = script.steps.get(poll__name='autoreg_name').poll
    org_poll = script.steps.get(poll__name='autoreg_org').poll
    field_poll = script.steps.get(poll__name='autoreg_field').poll
    division_poll = script.steps.get(poll__name='autoreg_division').poll
    building_poll = script.steps.get(poll__name='autoreg_building').poll

    org = find_best_response(session, org_poll)
    org = find_closest_match(org, Group.objects) if org else None
    contact.groups.add(org or Group.objects.get(name='Other Organizations'))

    field = find_best_response(session, field_poll)
    field = find_closest_match(field, Group.objects) if field else None
    contact.groups.add(field or Group.objects.get(name='Other Fields'))

    contact.name = find_best_response(session, name_poll) or 'Anonymous User'
    contact.name = ' '.join([n.capitalize() for n in contact.name.lower().split()])
    contact.name = contact.name[:100]

    division = find_best_response(session, division_poll)
    schools = School.objects
    facilities = HealthFacility.objects
    if division:
        division = find_closest_match(division, Location.objects.filter(type__name='division'))
        if division:
            contact.reporting_location = division
            schools = School.objects.filter(location__in=division.get_descendants(include_self=True))
            facilities = HealthFacility.objects.filter(catchment_areas__in=division.get_descendants(include_self=True))

    building = find_best_response(session, building_poll)
    if building:
        contact.school = find_closest_match(building, schools)
        contact.health_facility = find_closest_match(building, facilities)

    contact.save()


def get_polls(**kwargs):
    return Poll.objects.exclude(pk__in=ScriptStep.objects.exclude(poll=None).values_list('poll__pk', flat=True)).annotate(Count('responses'))
