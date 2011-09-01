from django import template

def get_district(location):
    try:
        return location.get_ancestors().get(kind__name='district').name
    except:
        return None

register = template.Library()
register.filter('get_district', get_district)
