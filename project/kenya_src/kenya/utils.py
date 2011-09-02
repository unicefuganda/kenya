from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from rapidsms_xforms.models import XForm, XFormField, XFormFieldConstraint, XFormSubmission
from script.models import Script, ScriptStep, ScriptSession
from script.utils.handling import find_closest_match, find_best_response
from poll.models import Poll
from rapidsms.models import Contact
from rapidsms.contrib.locations.models import Location
from django.db.models import Count
from healthmodels.models import HealthProvider, HealthFacility
import datetime
from rapidsms_httprouter.models import Message
from ureport.models import MassText
from poll.models import Poll


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
        ('b_measlvac', 'int', 'boys measles vaccination', True),
        ('g_measlvac', 'int', 'girls measles vaccination', True),
        ('b_immm', 'int', 'boys full vaccination', True),
        ('g_immm', 'int', 'girls full vaccination', True),
        ('kits', 'int', 'emergency health kits', True),
        ('stockout', 'int', 'stock outs', True),
    ],
    'nut':[
        ('sam', 'int', 'SAM', True),
        ('mam', 'int', 'MAM', True),
        ('recover', 'int', 'recovered', True),
        ('death', 'int', 'deaths', True),
    ],
    'cfp':[
        ('attm0', 'int', 'CFP 0-3(m)', True),
        ('attf0', 'int', 'CFP 0-3(f)', True),
        ('attm4', 'int', 'CFP 4-5(m)', True),
        ('attf4', 'int', 'CFP 4-5(f)', True),
        ('attm5', 'int', 'CFP 5-10(m)', True),
        ('attf5', 'int', 'CFP 5-10(f)', True),
        ('attm10', 'int', 'CFP 10+(m)', True),
        ('attf10', 'int', 'CFP 10+(f)', True),
    ],
    'child':[
        ('attm0', 'int', 'CFP 0-3(m)', True),
        ('attf0', 'int', 'CFP 0-3(f)', True),
        ('attm4', 'int', 'CFP 4-5(m)', True),
        ('attf4', 'int', 'CFP 4-5(f)', True),
        ('attm5', 'int', 'CFP 5-10(m)', True),
        ('attf5', 'int', 'CFP 5-10(f)', True),
        ('attm10', 'int', 'CFP 10+(m)', True),
        ('attf10', 'int', 'CFP 10+(f)', True),
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

        district_poll = Poll.objects.create(
            user=user, \
            type='district', \
            name='autoreg_district',
            question='What is the name of the district you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=district_poll,
            order=3,
            rule=ScriptStep.STRICT_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        division_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='autoreg_division',
            question='What is the name of the division you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=division_poll,
            order=4,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        const_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='autoreg_constituencey',
            question='What is the name of the constituencey you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=const_poll,
            order=5,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        facility_poll = Poll.objects.create(
            user=user, \
            type=Poll.TYPE_TEXT, \
            name='autoreg_facility',
            question='What is the name of the facility you work in?', \
            default_response='', \
        )
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=facility_poll,
            order=6,
            rule=ScriptStep.RESEND_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))

        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome to the UNICEF Kenya data collection system. You are now a fully registered member. Your timely reports are very import to us!",
            order=7,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=60,
            giveup_offset=0,
        ))
        for poll in [name_poll, org_poll, field_poll, district_poll, division_poll, const_poll, facility_poll]:
            poll.sites.add(Site.objects.get_current())

def init_groups():
    for g in ['UNICEF', 'NGO', 'Government', 'Other Organizations', 'Health', 'Education', 'Child Protection', 'WASH', 'Other Fields']:
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
    district_poll = script.steps.get(poll__name='autoreg_district').poll
    division_poll = script.steps.get(poll__name='autoreg_division').poll
    constituencey_poll = script.steps.get(poll__name='autoreg_constituencey').poll
    facility_poll = script.steps.get(poll__name='autoreg_facility').poll

    org = find_best_response(session, org_poll)
    org = find_closest_match(org, Group.objects) if org else Group.objects.get(name='Other Organizations')
    contact.groups.add(org)

    field = find_best_response(session, field_poll)
    field = find_closest_match(field, Group.objects) if field else Group.objects.get(name='Other Fields')
    contact.groups.add(field)

    contact.name = find_best_response(session, name_poll) or 'Anonymous User'
    contact.name = ' '.join([n.capitalize() for n in contact.name.lower().split()])
    contact.name = contact.name[:100]

    contact.reporting_location = find_best_response(session, district_poll)
    division = find_best_response(session, division_poll)
    if division:
        tosearch = contact.reporting_location.get_descendants() if contact.reporting_location else \
                    Location.objects.filter(type__name='district')
        division = find_closest_match(division, tosearch)
    if division:
        contact.reporting_location = division

    constituencey = find_best_response(session, constituencey_poll)
    if constituencey:
        tosearch = contact.reporting_location.get_descendants() if contact.reporting_location else \
                    Location.objects.exclude(type__name__in=['country', 'district', 'division'])
        constituencey = find_closest_match(constituencey, tosearch)
    if constituencey:
        contact.reporting_location = constituencey

    healthfacility = find_best_response(session, facility_poll)
    if healthfacility:
        facility = find_closest_match(healthfacility, HealthFacility.objects)
        if facility:
            contact.facility = facility
    contact.save()


def get_polls(**kwargs):
    return Poll.objects.exclude(pk__in=ScriptStep.objects.values_list('poll__pk', flat=True)).annotate(Count('responses'))
