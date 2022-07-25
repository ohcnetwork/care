import json
import time

import requests
from django.conf import settings


class ICDScraper:
    def __init__(self):
        self.root_concept_url = settings.ICD_SCRAPER_ROOT_CONCEPTS_URL
        self.child_concept_url = settings.ICD_SCRAPER_CHILD_CONCEPTS_URL
        self.scraped_concepts = []

    def add_query(self, url, query={}):
        return url + "?" + "&".join(map(lambda k: str(k) + "=" + str(query[k]), query.keys()))

    def get_child_concepts(self, p_concept, p_id):
        self.scraped_concepts.append({**p_concept, 'parentId': p_id})

        print(f"[+] Added {p_concept['label']}")

        if p_concept['isLeaf']:
            return

        concepts = []
        try:
            concepts = requests.get(self.add_query(self.child_concept_url, {
                'useHtml': 'false',
                'ConceptId': p_concept['ID'],
            })).json()
        except Exception as e:
            print("[x] Error encountered: ", e)
            with open('error.txt', 'a') as error_file:
                error_file.write(f"{p_concept['label']}\n")

            time.sleep(10)
            concepts = requests.get(self.add_query(self.child_concept_url, {
                'useHtml': 'false',
                'ConceptId': p_concept['ID'],
            })).json()

        for concept in concepts:
            self.get_child_concepts(concept, p_concept['ID'])

    def scrape(self):
        self.scraped_concepts = []
        root_concepts = requests.get(self.add_query(
            self.root_concept_url, {'useHtml': 'false'})).json()

        skip = [
            "24 Factors influencing health status or contact with health services",
            "25 Codes for special purposes",
            "26 Supplementary Chapter Traditional Medicine Conditions - Module I",
            "V Supplementary section for functioning assessment",
            "X Extension Codes"
        ]

        for root_concept in root_concepts:
            if root_concept['label'] in skip:
                continue

            self.get_child_concepts(root_concept, None)
            time.sleep(3)

        with open('data.json', 'w') as json_file:
            json.dump(self.scraped_concepts, json_file)
