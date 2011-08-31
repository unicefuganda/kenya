from django.contrib.auth.models import User, Group
from rapidsms_xforms.models import XForm, XFormField, XFormFieldConstraint
from script.models import Script, ScriptStep
from poll.models import Poll

DISEASE_CHOICES = [
    ('bd', 'int', 'Bloody diarrhea (Dysentery)', False),
    ('dy', 'int', 'Dysentery', False),
    ('ma', 'int', 'Malaria', False),
    ('tb', 'int', 'Tuberculosis', False),
    ('ab', 'int', 'Animal Bites', False),
    ('af', 'int', 'Acute Flaccid Paralysis (Polio)', False),
    ('mg', 'int', 'Meningitis', False),
    ('me', 'int', 'Measles', False),
    ('ch', 'int', 'Cholera', False),
    ('gw', 'int', 'Guinea Worm', False),
    ('nt', 'int', 'Neonatal Tetanus', False),
    ('yf', 'int', 'Yellow Fever', False),
    ('pl', 'int', 'Plague', False),
    ('ra', 'int', 'Rabies', False),
    ('rb', 'int', 'Rabies', False),
    ('vf', 'int', 'Other Viral Hemorrhagic Fevers', False),
    ('ei', 'int', 'Other Emerging Infectious Diseases', False),
]

HOME_ATTRIBUTES = [
   ('to', 'int', 'Total Homesteads Visited', False),
   ('it', 'int', 'ITTNs/LLINs', False),
   ('la', 'int', 'Latrines', False),
   ('ha', 'int', 'Handwashing Facilities', False),
   ('wa', 'int', 'Safe Drinking Water', False),
]

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
        ('sam', 'int', 'sam admissions', True),
        ('mam', 'int', 'mam admissions', True),
        ('recover', 'int', 'recovered from treatment', True),
        ('death', 'int', 'dead admittals', True),
    ],
    'cfp':[
        ('attm0', 'int', 'attendance m0-3', True),
        ('attf0', 'int', 'attendance f0-3', True),
        ('attm4', 'int', 'attendance m4-5', True),
        ('attf4', 'int', 'attendance f4-5', True),
        ('attm5', 'int', 'attendance m5-10', True),
        ('attf5', 'int', 'attendance f5-10', True),
        ('attm10', 'int', 'attendance m10+', True),
        ('attf10', 'int', 'attendance f10+', True),
    ],
    'child':[
        ('attm0', 'int', 'attendance m0-3', True),
        ('attf0', 'int', 'attendance f0-3', True),
        ('attm4', 'int', 'attendance m4-5', True),
        ('attf4', 'int', 'attendance f4-5', True),
        ('attm5', 'int', 'attendance m5-10', True),
        ('attf5', 'int', 'attendance f5-10', True),
        ('attm10', 'int', 'attendance m10+', True),
        ('attf10', 'int', 'attendance f10+', True),
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


def init_autoreg(sender, **kwargs):
    script, created = Script.objects.get_or_create(
            slug="autoreg", defaults={
            'name':"Default autoregistration script"})
    if created:
        user, created = User.objects.get_or_create(username="admin")

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
            question='What is the name of the constituencey you work in?', \
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
        init_xforms(sender)
        init_autoreg(sender)
        structures_initialized = True
