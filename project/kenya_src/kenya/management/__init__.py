from django.db.models.signals import post_syncdb
from kenya.utils import init_structures

post_syncdb.connect(init_structures, weak=False)
