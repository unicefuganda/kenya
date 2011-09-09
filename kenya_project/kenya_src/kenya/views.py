from poll.models import Poll, Response
from rapidsms.models import Contact
from generic.views import generic
from ureport.forms import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import  render_to_response, redirect, get_object_or_404

@login_required
def view_responses(req, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    responses = poll.responses.all()
    responses = responses.order_by('-date')
    response_rates = {}
    for group in req.user.groups.all():
        try:
            contact_count = poll.contacts.filter(groups__in=[group]).distinct().count()
            response_count = poll.responses.filter(contact__groups__in=[group]).distinct().count()
            response_rates[str(group.name)] = [contact_count]
            response_rates[str(group.name)].append(response_count)
            response_rates[str(group.name)].append(response_count * 100.0 / contact_count)

        except(ZeroDivisionError):
            response_rates.pop(group.name)
    typedef = Poll.TYPE_CHOICES[poll.type]
    columns = [('Sender', False, 'sender', None)]
    for column, style_class in typedef['report_columns']:
        columns.append((column, False, style_class, None))

    return generic(req,
        model=Response,
        response_rates=response_rates,
        queryset=responses,
        objects_per_page=25,
        selectable=True,
        partial_base='kenya/partials/poll_partial_base.html',
        base_template='kenya/responses_base.html',
        row_base=typedef['view_template'],
        action_forms=[AssignToPollForm],
        filter_forms=[SearchResponsesForm],
        columns=columns,
        partial_row='ureport/partials/polls/response_row.html'
    )
