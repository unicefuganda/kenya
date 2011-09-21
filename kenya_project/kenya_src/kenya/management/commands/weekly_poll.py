from optparse import make_option
from poll.models import Poll
from rapidsms.models import Contact
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import datetime

class Command(BaseCommand):

    help = """Creates a weekly yes/no poll about water sources"""

    option_list = BaseCommand.option_list + (
    make_option("--open", action="store_true", dest="open"),
    make_option("--close", action="store_true", dest="close"),
    )

    def handle(self, **options):
        open = options["open"]
        close = options["close"]
        d = datetime.datetime.now()
        poll_name = "%s Regular Wash Poll" % d.strftime("%Y-%m-%d")
        user = User.objects.get(username='admin')
        if open:
            p = Poll.create_with_bulk(name=poll_name,
                                    question='',
                                    default_response='',
                                    user=user,
                                    contacts=Contact.objects.all(),
                                    type=Poll.TYPE_TEXT,
                                    )
            p.add_yesno_categories()
            p.start()
        elif close:
            polls = Poll.objects.filter(name__endswith='Regular Wash Poll', end_date=None)
            if polls.count():
                p = polls.order_by('-name')[0]
                p.end()
