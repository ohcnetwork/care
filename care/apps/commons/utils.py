import csv
import json
from django.conf import settings


def get_json_fixtures(fixtures):
    json_fixtures = []
    json_fixtures_name = []

    for fixture in fixtures:
        data = []
        csv_file_name = fixture[0]
        model = fixture[1]
        csv_file_absolute_path = get_absolute_path(csv_file_name)
        json_file_absolute_path = get_absolute_path(csv_file_name.split(".")[0] + ".json")

        with open(csv_file_absolute_path) as csvFile:
            csvReader = csv.DictReader(csvFile)
            for rows in csvReader:
                data.append({"pk": rows["id"], "model": model, "fields": rows})

        with open(json_file_absolute_path, "w") as json_file:
            json_file.write(json.dumps(data, indent=4))

        fixture_name = csv_file_name.split("/")[-1].split(".")[0]
        json_fixtures_name.append(fixture_name)
        json_fixtures.append(json_file_absolute_path)

    return json_fixtures, json_fixtures_name


def get_absolute_path(file_name):
    return settings.BASE_DIR + "/" + file_name
