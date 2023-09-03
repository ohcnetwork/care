import json
import logging
import time

import requests
from django.conf import settings

# ruff: noqa: G004
logger = logging.getLogger(__name__)

ICD_REQUEST_TIMEOUT = 30


class ICDScraper:
    def __init__(self):
        self.root_concept_url = settings.ICD_SCRAPER_ROOT_CONCEPTS_URL
        self.child_concept_url = settings.ICD_SCRAPER_CHILD_CONCEPTS_URL
        self.scraped_concepts = []
        self.scraped_concept_dict = {}

    def get_child_concepts(self, p_concept, p_parent_id):
        if p_concept["ID"] in self.scraped_concept_dict:
            logger.info(f"[-] Skipped duplicate, {p_concept['label']}")
            return

        self.scraped_concepts.append({**p_concept, "parentId": p_parent_id})
        self.scraped_concept_dict[p_concept["ID"]] = True

        logger.info(f"[+] Added {p_concept['label']}")

        if p_concept["isLeaf"]:
            return

        concepts = []
        try:
            concepts = requests.get(
                self.child_concept_url,
                params={
                    "useHtml": "false",
                    "ConceptId": p_concept["ID"],
                },
                timeout=ICD_REQUEST_TIMEOUT,
            ).json()
        except Exception as e:
            logger.error("[x] Error encountered", exc_info=e)
            with open("error.txt", "a") as error_file:
                error_file.write(f"{p_concept['label']}\n")

            time.sleep(10)
            concepts = requests.get(
                self.child_concept_url,
                params={
                    "useHtml": "false",
                    "ConceptId": p_concept["ID"],
                },
                timeout=ICD_REQUEST_TIMEOUT,
            ).json()

        for concept in concepts:
            self.get_child_concepts(concept, p_concept["ID"])

    def scrape(self):
        self.scraped_concepts = []
        self.scraped_concept_dict = {}
        root_concepts = requests.get(
            self.root_concept_url,
            params={"useHtml": "false"},
            timeout=ICD_REQUEST_TIMEOUT,
        ).json()

        skip = [
            "V Supplementary section for functioning assessment",
            "X Extension Codes",
        ]

        for root_concept in root_concepts:
            if root_concept["label"] in skip:
                continue

            self.get_child_concepts(root_concept, None)
            time.sleep(3)

        with open("data.json", "w") as json_file:
            json.dump(self.scraped_concepts, json_file)
