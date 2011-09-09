from django import template

def get_district(location):
    try:
        return location.get_ancestors().get(type__name='district').name
    except:
        return None

def latest(obj):
    try:
        return XFormSubmission.objects.filter(connection__in=obj.connection_set.all()).latest('created').created
    except:
        return None

register = template.Library()
register.filter('get_district', get_district)
register.filter('latest', latest)
