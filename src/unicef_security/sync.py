import json
import logging

import requests
from django_countries import countries
from requests.auth import HTTPBasicAuth

from . import config
from .graph import SyncResult
from .models import BusinessArea, Region

logger = logging.getLogger(__name__)

c = dict(countries)


def get_vision_auth():
    return HTTPBasicAuth(config.VISION_USER, config.VISION_PASSWORD)


def load_region():
    url = "{}GetBusinessAreaList_JSON".format(config.INSIGHT_URL)
    response = requests.get(url, auth=get_vision_auth()).json()
    data = json.loads(response['GetBusinessAreaList_JSONResult'])
    results = SyncResult()
    regions = set((e['REGION_CODE'], e['REGION_NAME']) for e in data)

    for entry in regions:
        region, created = Region.objects.update_or_create(code=entry[0],
                                                          defaults={
                                                              'name': entry[1]}
                                                          )
        results.log(region, created)
    logger.info(f"Region sync completed: {results}")
    return results


def load_business_area():
    url = "{}GetBusinessAreaList_JSON".format(config.INSIGHT_URL)
    response = requests.get(url, auth=get_vision_auth()).json()
    data = json.loads(response['GetBusinessAreaList_JSONResult'])
    results = SyncResult()
    for entry in data:
        defaults = {'name': entry['BUSINESS_AREA_NAME'],
                    'long_name': entry['BUSINESS_AREA_LONG_NAME'],
                    'country': countries.by_name(entry['BUSINESS_AREA_NAME']),
                    'region': Region.objects.get_or_create(code=entry['REGION_CODE'],
                                                           defaults={
                                                               'name': entry['REGION_NAME']}
                                                           )[0]
                    }
        area, created = BusinessArea.objects.update_or_create(code=entry['BUSINESS_AREA_CODE'],
                                                              defaults=defaults)
        results.log(area, created)
    logger.info(f"BusinessArea sync completed: {results}")
    return results
