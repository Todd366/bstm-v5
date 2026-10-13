#!/usr/bin/env python3

import json
import os

DATA_DIR = "data"

FILES = {
    "youth": "data/youth.json",
    "businesses": "data/businesses.json",
    "opportunities": "data/opportunities.json",
    "trials": "data/trials.json",
    "departments": "data/departments.json",
    "activity": "data/activity.json",
    "capabilities": "data/capabilities.json",
    "matches": "data/matches.json",
    "audits": "data/audits.json",
    "evidence": "data/evidence.json",
    "pathways": "data/pathways.json",
    "graph": "data/graph.json"
}


def load(key):
    path = FILES[key]

    if not os.path.exists(path):
        return [] if key != "graph" else {
            "nodes": [],
            "edges": []
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(key, data):
    with open(
        FILES[key],
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def repair_youth():

    youth = load("youth")

    before = len(youth)

    cleaned = []

    for person in youth:

        name = str(
            person.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            print(
                "Removing invalid youth:",
                person.get(
                    "id",
                    "UNKNOWN"
                )
            )
            continue

        cleaned.append(person)

    save(
        "youth",
        cleaned
    )

    return before, len(cleaned)


def repair_businesses():

    businesses = load("businesses")

    before = len(businesses)

    cleaned = []

    for business in businesses:

        name = str(
            business.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            print(
                "Removing invalid business:",
                business.get(
                    "id",
                    "UNKNOWN"
                )
            )
            continue

        cleaned.append(
            business
        )

    save(
        "businesses",
        cleaned
    )

    return before, len(cleaned)


def repair_opportunities():

    opportunities = load(
        "opportunities"
    )

    cleaned = []

    for opportunity in opportunities:

        if not opportunity.get(
            "id"
        ):
            continue

        if not opportunity.get(
            "title"
        ):
            continue

        cleaned.append(
            opportunity
        )

    save(
        "opportunities",
        cleaned
    )


def repair_trials():

    trials = load(
        "trials"
    )

    cleaned = []

    for trial in trials:

        if not trial.get(
            "id"
        ):
            continue

        if not trial.get(
            "title"
        ):
            continue

        cleaned.append(
            trial
        )

    save(
        "trials",
        cleaned
    )


def repair_matches():

    matches = load(
        "matches"
    )

    cleaned = []

    for match in matches:

        if (
            match.get(
                "youth_id"
            )
            and
            match.get(
                "opportunity_id"
            )
        ):

            cleaned.append(
                match
            )

    save(
        "matches",
        cleaned
    )


def main():

    print(
        "=========================================="
    )

    print(
        "BSTM DATA REPAIR ENGINE"
    )

    print(
        "=========================================="
    )

    youth_before, youth_after = repair_youth()

    business_before, business_after = repair_businesses()

    repair_opportunities()

    repair_trials()

    repair_matches()

    print(
        "\nREPAIR COMPLETE"
    )

    print(
        "Youth:",
        youth_before,
        "→",
        youth_after
    )

    print(
        "Businesses:",
        business_before,
        "→",
        business_after
    )

    print(
        "\nYour valid records have been preserved."
    )


if __name__ == "__main__":
    main()

