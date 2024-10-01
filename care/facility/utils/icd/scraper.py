import json
import logging
import time
from typing import TYPE_CHECKING

import requests
from django.conf import settings

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class ICDScraper:
    def __init__(self):
        self.root_concept_url = settings.ICD_SCRAPER_ROOT_CONCEPTS_URL
        self.child_concept_url = settings.ICD_SCRAPER_CHILD_CONCEPTS_URL
        self.scraped_concepts = []
        self.scraped_concept_dict = {}
        self.request_timeout = 10

    def add_query(self, url, query=None):
        if query is None:
            query = {}
        return url + "?" + "&".join(str(k) + "=" + str(query[k]) for k in query)

    def get_child_concepts(self, p_concept, p_parent_id):
        if p_concept["ID"] in self.scraped_concept_dict:
            logger.info("[-] Skipped duplicate, %s", p_concept["label"])
            return

        self.scraped_concepts.append({**p_concept, "parentId": p_parent_id})
        self.scraped_concept_dict[p_concept["ID"]] = True

        logger.info("[+] Added %s", p_concept["label"])

        if p_concept["isLeaf"]:
            return

        concepts = []
        try:
            concepts = requests.get(
                self.add_query(
                    self.child_concept_url,
                    {
                        "useHtml": "false",
                        "ConceptId": p_concept["ID"],
                    },
                ),
                timeout=self.request_timeout,
            ).json()
        except Exception as e:
            logger.info("[x] Error encountered: %s", e)
            error_file: Path = settings.BASE_DIR / "error.txt"
            with error_file.open("a") as ef:
                ef.write(f"{p_concept['label']}\n")

            time.sleep(10)
            concepts = requests.get(
                self.add_query(
                    self.child_concept_url,
                    {
                        "useHtml": "false",
                        "ConceptId": p_concept["ID"],
                    },
                ),
                timeout=self.request_timeout,
            ).json()

        for concept in concepts:
            self.get_child_concepts(concept, p_concept["ID"])

    def scrape(self):
        self.scraped_concepts = []
        self.scraped_concept_dict = {}
        root_concepts = requests.get(
            self.add_query(self.root_concept_url, {"useHtml": "false"}),
            timeout=self.request_timeout,
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

        data_file: Path = settings.BASE_DIR / "data" / "icd11.json"
        with data_file.open("w") as json_file:
            json.dump(self.scraped_concepts, json_file)
