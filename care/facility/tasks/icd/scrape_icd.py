import json

import celery
from django.db import transaction

from care.facility.models.icd import ICDDisease
from care.facility.tasks.icd.scraper import ICDScraper


@celery.task()
def scrape_icd():
    scraper = ICDScraper()
    scraper.scrape()

    with open('data.json', 'r') as json_file:
        concepts = json.load(json_file)

        with transaction.atomic():
            for concept in concepts:
                if not ICDDisease.objects.filter(pk=concept['ID']).exists():
                    disease = ICDDisease(
                        concept['ID'],
                        concept['label'],
                        concept['isLeaf'],
                        concept['classKind'],
                        concept['isAdoptedChild'],
                        concept['averageDepth'],
                        concept['parentId']
                    )
                    disease.save()
