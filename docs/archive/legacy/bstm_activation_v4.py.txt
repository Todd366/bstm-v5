#!/usr/bin/env python3

import json
import os
import uuid
from datetime import datetime, timezone

# ============================================================
# BSTM ACTIVATION ENGINE V4
# FOUNDATION CORE
# ============================================================

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

DEFAULTS = {
    "youth": [],
    "businesses": [],
    "opportunities": [],
    "trials": [],
    "departments": [],
    "activity": [],
    "capabilities": [],
    "matches": [],
    "audits": [],
    "evidence": [],
    "pathways": [],
    "graph": {
        "nodes": [],
        "edges": []
    }
}


# ============================================================
# TIME + IDENTITY
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def uid(prefix):
    return (
        prefix
        + "-"
        + str(
            uuid.uuid4()
        )[:8]
    )


# ============================================================
# DATA CORE
# ============================================================

def ensure_data():

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    for key, path in FILES.items():

        if not os.path.exists(path):

            save(
                key,
                DEFAULTS[key]
            )


def load(key):

    path = FILES[key]

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):

        data = DEFAULTS[key]

        save(
            key,
            data
        )

    return data


def save(key, data):

    path = FILES[key]

    temp_path = (
        path
        + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_path,
        path
    )


# ============================================================
# INPUT VALIDATION
# ============================================================

def ask_required(label):

    while True:

        value = input(
            label
        ).strip()

        if value:

            return value

        print(
            "This field is required."
        )


def ask_optional(label):

    return input(
        label
    ).strip()


def ask_number(
    label,
    minimum=None,
    maximum=None,
    default=None
):

    while True:

        raw = input(
            label
        ).strip()

        if not raw and default is not None:

            return default

        try:

            value = float(
                raw
            )

        except ValueError:

            print(
                "Enter a valid number."
            )

            continue

        if (
            minimum is not None
            and value < minimum
        ):

            print(
                f"Minimum: {minimum}"
            )

            continue

        if (
            maximum is not None
            and value > maximum
        ):

            print(
                f"Maximum: {maximum}"
            )

            continue

        return value


# ============================================================
# EVENT ENGINE
# ============================================================

def log_event(
    event_type,
    actor_id=None,
    target_id=None,
    details=None
):

    activity = load(
        "activity"
    )

    event = {

        "id":
            uid("EV"),

        "timestamp":
            now(),

        "event":
            event_type,

        "actor_id":
            actor_id,

        "target_id":
            target_id,

        "details":
            details or {}
    }

    activity.append(
        event
    )

    save(
        "activity",
        activity
    )

    return event


# ============================================================
# GRAPH ENGINE
# ============================================================

def add_node(
    node_id,
    node_type,
    label,
    metadata=None
):

    graph = load(
        "graph"
    )

    for node in graph[
        "nodes"
    ]:

        if node[
            "id"
        ] == node_id:

            return

    graph[
        "nodes"
    ].append({

        "id":
            node_id,

        "type":
            node_type,

        "label":
            label,

        "metadata":
            metadata or {}
    })

    save(
        "graph",
        graph
    )


def add_edge(
    source,
    relation,
    target,
    metadata=None
):

    graph = load(
        "graph"
    )

    for edge in graph[
        "edges"
    ]:

        if (

            edge[
                "source"
            ]
            == source

            and

            edge[
                "relation"
            ]
            == relation

            and

            edge[
                "target"
            ]
            == target

        ):

            return

    graph[
        "edges"
    ].append({

        "id":
            uid("EDGE"),

        "source":
            source,

        "relation":
            relation,

        "target":
            target,

        "metadata":
            metadata or {},

        "created_at":
            now()
    })

    save(
        "graph",
        graph
    )


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def exists_by_name(
    key,
    field,
    value
):

    value = value.lower().strip()

    for item in load(key):

        existing = str(
            item.get(
                field,
                ""
            )
        ).lower().strip()

        if existing == value:

            return item

    return None


# ============================================================
# YOUTH ACTIVATION
# ============================================================

def activate_youth():

    print(
        "\n=========================================="
    )

    print(
        "BSTM YOUTH ACTIVATION"
    )

    print(
        "=========================================="
    )

    name = ask_required(
        "Name: "
    )

    existing = exists_by_name(
        "youth",
        "name",
        name
    )

    if existing:

        print(
            "\nYouth already exists."
        )

        print(
            "ID:",
            existing["id"]
        )

        return

    location = ask_required(
        "Location: "
    )

    passion = ask_required(
        "Passion / interests: "
    )

    skills = ask_optional(
        "Existing skills: "
    )

    goal = ask_required(
        "Main goal: "
    )

    availability = ask_optional(
        "Availability: "
    )

    equipment = ask_optional(
        "Equipment / resources: "
    )

    youth_id = uid(
        "Y"
    )

    profile = {

        "id":
            youth_id,

        "name":
            name,

        "location":
            location,

        "passion":
            passion,

        "skills":
            skills,

        "goal":
            goal,

        "availability":
            availability,

        "equipment":
            equipment,

        "level":
            "Explorer",

        "capability_score":
            0,

        "learning_score":
            0,

        "reputation_score":
            50,

        "reliability_score":
            50,

        "completed_trials":
            0,

        "completed_opportunities":
            0,

        "revenue":
            0,

        "capabilities":
            [],

        "recommended_pathways":
            [],

        "skill_gaps":
            [],

        "unlocked_opportunities":
            [],

        "created_at":
            now()
    }

    youth = load(
        "youth"
    )

    youth.append(
        profile
    )

    save(
        "youth",
        youth
    )

    add_node(

        youth_id,

        "youth",

        name,

        {

            "passion":
                passion,

            "skills":
                skills,

            "goal":
                goal

        }

    )

    log_event(

        "youth_activated",

        actor_id=
            youth_id,

        target_id=
            youth_id,

        details=
            {

                "name":
                    name,

                "location":
                    location

            }

    )

    print(
        "\nYOUTH ACTIVATED"
    )

    print(
        "Activation ID:",
        youth_id
    )

    print(
        "Level:",
        profile[
            "level"
        ]
    )


# ============================================================
# BUSINESS ACTIVATION
# ============================================================

def activate_business():

    print(
        "\n=========================================="
    )

    print(
        "BSTM BUSINESS ACTIVATION"
    )

    print(
        "=========================================="
    )

    name = ask_required(
        "Business name: "
    )

    existing = exists_by_name(
        "businesses",
        "name",
        name
    )

    if existing:

        print(
            "\nBusiness already exists."
        )

        print(
            "ID:",
            existing["id"]
        )

        return

    owner = ask_required(
        "Owner / contact: "
    )

    sector = ask_required(
        "Sector: "
    )

    location = ask_required(
        "Location: "
    )

    problem = ask_required(
        "Main problem: "
    )

    business_id = uid(
        "B"
    )

    profile = {

        "id":
            business_id,

        "name":
            name,

        "owner":
            owner,

        "sector":
            sector,

        "location":
            location,

        "main_problem":
            problem,

        "audit_status":
            "Pending",

        "opportunities_generated":
            0,

        "created_at":
            now()
    }

    businesses = load(
        "businesses"
    )

    businesses.append(
        profile
    )

    save(
        "businesses",
        businesses
    )

    add_node(

        business_id,

        "business",

        name,

        {

            "sector":
                sector,

            "location":
                location

        }

    )

    log_event(

        "business_activated",

        actor_id=
            business_id,

        target_id=
            business_id,

        details=
            {

                "name":
                    name,

                "sector":
                    sector

            }

    )

    print(
        "\nBUSINESS ACTIVATED"
    )

    print(
        "Business ID:",
        business_id
    )


# ============================================================
# LIST RECORDS
# ============================================================

def list_youth():

    youth = load(
        "youth"
    )

    print(
        "\n=== ACTIVE YOUTH ==="
    )

    if not youth:

        print(
            "No valid youth records."
        )

        return

    for person in youth:

        print(

            f"{person['id']} | "

            f"{person['name']} | "

            f"{person.get('level', 'Explorer')} | "

            f"Trials: "

            f"{person.get('completed_trials', 0)} | "

            f"Reputation: "

            f"{person.get('reputation_score', 0)}"

        )


def list_businesses():

    businesses = load(
        "businesses"
    )

    print(
        "\n=== ACTIVE BUSINESSES ==="
    )

    if not businesses:

        print(
            "No valid businesses."
        )

        return

    for business in businesses:

        print(

            f"{business['id']} | "

            f"{business['name']} | "

            f"{business['sector']} | "

            f"Audit: "

            f"{business.get('audit_status', 'Pending')}"

        )


# ============================================================
# SYSTEM INTEGRITY
# ============================================================

def system_integrity():

    print(
        "\n=========================================="
    )

    print(
        "BSTM V4 SYSTEM INTEGRITY"
    )

    print(
        "=========================================="
    )

    for key in FILES:

        data = load(
            key
        )

        if isinstance(
            data,
            list
        ):

            print(
                f"{key}: {len(data)} records"
            )

        else:

            print(
                f"{key}: OK"
            )

    print(
        "\nCore integrity check complete."
    )


# ============================================================
# MAIN MENU
# ============================================================

def menu():

    ensure_data()

    while True:

        print(
            """
==================================================
 BSTM ACTIVATION ENGINE V4
 FOUNDATION CORE
==================================================

1. Activate Youth
2. Activate Business
3. List Youth
4. List Businesses
5. System Integrity
6. Exit

==================================================
"""
        )

        choice = input(
            "BSTM > "
        ).strip()

        if choice == "1":

            activate_youth()

        elif choice == "2":

            activate_business()

        elif choice == "3":

            list_youth()

        elif choice == "4":

            list_businesses()

        elif choice == "5":

            system_integrity()

        elif choice == "6":

            print(
                "\nBSTM V4 shutting down."
            )

            break

        else:

            print(
                "\nInvalid option."
            )


if __name__ == "__main__":

    menu()

