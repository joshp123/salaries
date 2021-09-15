import csv
import json
import math
import requests
import subprocess
from collections import defaultdict

from bs4 import BeautifulSoup


TIERS = ("tier-1", "tier-2", "tier-3")
SENIORITY_LEVELS = ("entry-level", "mid-level", "senior", "above-senior")

JS_EXTRA_LINES = """
var jsonified = JSON.stringify(COMPENSATION_LIST)
console.log(jsonified)
"""

all_datapoints = []
all_datapoints_dict = defaultdict(dict)


def extract_levels():
    base_url = "https://techpays.eu/countries/netherlands/{seniority}/{tier}"
    for tier in TIERS:
        for seniority in SENIORITY_LEVELS:
            url = base_url.format(seniority=seniority, tier=tier)
            output = requests.get(url).text
            soup = BeautifulSoup(output, "html.parser")
            compensation_data_js = [
                s.contents
                for s in soup.find_all("script")
                if s.string and "COMPENSATION_LIST" in s.string
            ][0][0]
            temp_js = f"/tmp/{seniority}_{tier}.js"
            with open(temp_js, "w") as f:
                f.write(compensation_data_js)
                f.write(JS_EXTRA_LINES)
            jsonified_output = subprocess.run(["node", temp_js], capture_output=True)
            compensation_list = json.loads(jsonified_output.stdout.decode("utf-8"))
            for item in compensation_list:
                item["tier"] = tier
                item["seniority"] = seniority
                all_datapoints.append(item)

            all_datapoints_dict[tier][seniority] = compensation_list

    with open("techpays_data.csv", "w", encoding="utf8", newline="") as output_file:
        fc = csv.DictWriter(
            output_file,
            fieldnames=all_datapoints[0].keys(),
        )
        fc.writeheader()
        fc.writerows(all_datapoints)


def percentile(data, percentile):
    n = len(data)
    p = n * percentile / 100
    if p.is_integer():
        return sorted(data)[int(p)]
    else:
        return sorted(data)[int(math.ceil(p)) - 1]


def print_stats():
    for tier in TIERS:
        for seniority in SENIORITY_LEVELS:
            base_dataset = [
                i["baseSalaryNumber"] for i in all_datapoints_dict[tier][seniority]
            ]
            total_comp_dataset = [
                i["totalCompensationNumber"]
                for i in all_datapoints_dict[tier][seniority]
            ]
            base_p50 = percentile(base_dataset, 50)
            base_p75 = percentile(base_dataset, 75)
            base_p90 = percentile(base_dataset, 90)
            total_comp_p50 = percentile(total_comp_dataset, 50)
            total_comp_p75 = percentile(total_comp_dataset, 75)
            total_comp_p90 = percentile(total_comp_dataset, 90)
            print(f"{tier} - {seniority} - datapoints used: {len(base_dataset)}")
            print(f"{tier} - {seniority} - base p50 = {base_p50}")
            print(f"{tier} - {seniority} - base p75 = {base_p75}")
            print(f"{tier} - {seniority} - base p90 = {base_p90}")
            print(f"{tier} - {seniority} - total_comp p50 = {total_comp_p50}")
            print(f"{tier} - {seniority} - total_comp p75 = {total_comp_p75}")
            print(f"{tier} - {seniority} - total_comp p90 = {total_comp_p90}")


def main():
    extract_levels()
    print_stats()


if __name__ == "__main__":
    main()
