from rapidsms.models import Contact
from django.conf import settings
from rapidsms.apps.base import AppBase
from script.models import ScriptProgress, Script
from unregister.models import Blacklist

class App (AppBase):

    def handle (self, message):
        opt_out_words = getattr(settings, 'OPT_OUT_WORDS', [])
        print "ACTIVATION CODE IS %s" % getattr(settings, 'ACTIVATION_CODE', 'NOT IN SETTINGS')
        print "OPT_OUT_WORDS ARE %s" % str(opt_out_words)
        print "MESSAGE IS '%s'" % message.text.strip().lower()
        print "MESSAGE IS AN OPT OUT WORD? %s" % str(message.text.strip().lower() in opt_out_words)
        if getattr(settings, 'ACTIVATION_CODE', None) and message.text.strip().lower() == settings.ACTIVATION_CODE:
            if not message.connection.contact:
                message.respond('You must first register with the system.Text JOIN to 6767 to begin.')
                return True
            if not message.connection.contact.active:
                message.connection.contact.active = True
                message.connection.contact.save()
                message.respond(getattr(settings, 'ACTIVATION_MESSAGE', 'Congratulations, you are now active in the system!'))
                return True
            else:
                message.respond(getattr(settings, 'ALREADY_ACTIVATED_MESSAGE', 'You are already in the system.You should not SMS the code %s' % getattr(settings, 'ACTIVATION_CODE')))
                return True
        elif message.text.strip().lower() in getattr(settings, 'OPT_OUT_WORDS', []):
            Blacklist.objects.create(connection=message.connection)
            if (message.connection.contact):
                message.connection.contact.active = False
                message.connection.contact.save()
            message.respond(getattr(settings, 'OPT_OUT_CONFIRMATION', ''))
            return True
        elif message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_IN_WORDS', [])]:
            if Blacklist.objects.filter(connection=message.connection).count() or not message.connection.contact:
                for b in Blacklist.objects.filter(connection=message.connection):
                    b.delete()
                ScriptProgress.objects.create(script=Script.objects.get(slug="autoreg"), \
                                          connection=message.connection)
            else:
                message.repond("You are already in the system and do not need to 'Join' again.Only if you want to reregister,or change location,please send the word JOIN to 6767.")
            return True
        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
        return False

    def outgoing(self, msg):
        if Blacklist.objects.filter(connection=msg.connection).count():
            return False
        return True
