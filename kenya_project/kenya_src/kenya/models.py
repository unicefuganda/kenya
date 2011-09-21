from django.db.models.signals import post_syncdb
from .utils import do_autoreg, xform_received_handler, init_structures
from script.signals import script_progress_was_completed
from rapidsms_xforms.models import xform_received

script_progress_was_completed.connect(do_autoreg, weak=False)
xform_received.connect(xform_received_handler, weak=True)
post_syncdb.connect(init_structures, weak=False)
