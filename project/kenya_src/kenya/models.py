from .utils import do_autoreg, xform_received_handler
from script.signals import script_progress_was_completed
from rapidsms_xforms.models import xform_received

script_progress_was_completed.connect(do_autoreg, weak=False)
xform_received.connect(xform_received_handler, weak=True)
