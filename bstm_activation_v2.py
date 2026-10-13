#!/usr/bin/env python3

import json
import os
import uuid
from datetime import datetime, timezone
from collections import defaultdict

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
# CORE
# ============================================================

def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return f"{prefix}-{str(uuid.uuid4())[:8]}"


def ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    for key, path in FILES.items():
        if not os.path.exists(path):
            save(key, DEFAULTS[key])


def load(key):
    with open(FILES[key], "r", encoding="utf-8") as f:
        return json.load(f)


def save(key, data):
    with open(FILES[key], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log_event(event_type, details):
    activity = load("activity")

    activity.append({
        "id": uid("EV"),
        "timestamp": now(),
        "event": event_type,
        "details": details
    })

    save("activity", activity)


# ============================================================
# GRAPH ENGINE
# ============================================================

def add_node(node_id, node_type, label, metadata=None):
    graph = load("graph")

    if not any(n["id"] == node_id for n in graph["nodes"]):
        graph["nodes"].append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "metadata": metadata or {}
        })

        save("graph", graph)


def add_edge(source, relation, target, metadata=None):
    graph = load("graph")

    edge = {
        "id": uid("EDGE"),
        "source": source,
        "relation": relation,
        "target": target,
        "metadata": metadata or {},
        "created_at": now()
    }

    graph["edges"].append(edge)

    save("graph", graph)


# ============================================================
# DEPARTMENTS
# ============================================================

DEPARTMENTS = [
    "AI & Machine Learning",
    "Trading Automation",
    "VPN & Network Security",
    "Web Development",
    "Mobile Application Development",
    "System Integration & API",
    "Data Science & Analytics",
    "Blockchain & Cryptocurrency",
    "Graphic Design & Branding",
    "Content Creation & Copywriting",
    "Social Media Management",
    "Digital Marketing & Advertising",
    "BSTM Tutorial Center",
    "Private Security",
    "Music Department",
    "CabLink Transportation",
    "Finance & Accounting",
    "Marketplace & E-Commerce",
    "Research & Development",
    "Healthcare Information & Wellness",
    "Nutrition & Health Products",
    "Micro Farming & Urban Agriculture",
    "Sustainability & Environment",
    "Human Resources & Talent Development",
    "Project Management Office",
    "Legal & Compliance",
    "G.I.N — Global Intelligence Network",
    "BSTM Clothing Brand",
    "Spiritual Guidance & Consciousness",
    "BHD — Black Hole Drive"
]


def initialize_departments():
    departments = load("departments")

    existing = {d["name"] for d in departments}

    for name in DEPARTMENTS:
        if name not in existing:
            department = {
                "id": uid("D"),
                "name": name,
                "status": "Active",
                "created_at": now()
            }

            departments.append(department)

            add_node(
                department["id"],
                "department",
                name
            )

    save("departments", departments)


# ============================================================
# YOUTH ACTIVATION
# ============================================================

def register_youth():

    print("\n========================================")
    print("BSTM YOUTH ACTIVATION")
    print("========================================")

    name = input("Name: ").strip()
    location = input("Location: ").strip()

    passion = input(
        "What are you passionate about? "
    ).strip()

    skills = input(
        "What skills do you already have? "
    ).strip()

    goal = input(
        "What do you want to achieve? "
    ).strip()

    availability = input(
        "How much time can you commit? "
    ).strip()

    equipment = input(
        "What equipment do you have? "
    ).strip()

    youth_id = uid("Y")

    profile = {
        "id": youth_id,
        "name": name,
        "location": location,
        "passion": passion,
        "skills": skills,
        "goal": goal,
        "availability": availability,
        "equipment": equipment,

        "level": "Explorer",

        "capability_score": 0,
        "learning_score": 0,
        "reputation_score": 0,
        "reliability_score": 0,

        "completed_trials": 0,
        "completed_opportunities": 0,
        "revenue": 0,

        "capabilities": [],
        "recommended_pathways": [],
        "unlocked_opportunities": [],

        "created_at": now()
    }

    youth = load("youth")
    youth.append(profile)
    save("youth", youth)

    add_node(
        youth_id,
        "youth",
        name,
        {
            "passion": passion,
            "skills": skills
        }
    )

    print("\nAnalyzing passion and capability pathways...")

    pathways = generate_pathways(profile)

    profile["recommended_pathways"] = pathways

    youth = load("youth")

    for y in youth:
        if y["id"] == youth_id:
            y.update(profile)

    save("youth", youth)

    log_event(
        "youth_activated",
        {
            "youth_id": youth_id,
            "pathways": pathways
        }
    )

    print("\n----------------------------------------")
    print("YOUTH ACTIVATED")
    print("----------------------------------------")
    print("Activation ID:", youth_id)
    print("Level:", profile["level"])

    print("\nRecommended Pathways:")

    for pathway in pathways:
        print(" →", pathway)


# ============================================================
# PASSION → CAPABILITY PATHWAY ENGINE
# ============================================================

def generate_pathways(profile):

    text = (
        profile["passion"] + " " +
        profile["skills"] + " " +
        profile["goal"]
    ).lower()

    pathways = []

    mapping = {
        "tech": [
            "Web Development",
            "AI & Machine Learning",
            "System Integration & API"
        ],

        "computer": [
            "Web Development",
            "System Integration & API",
            "AI & Machine Learning"
        ],

        "program": [
            "Web Development",
            "Mobile Application Development",
            "AI & Machine Learning"
        ],

        "ai": [
            "AI & Machine Learning",
            "Data Science & Analytics"
        ],

        "business": [
            "Finance & Accounting",
            "Digital Marketing & Advertising",
            "Research & Development"
        ],

        "marketing": [
            "Digital Marketing & Advertising",
            "Social Media Management",
            "Content Creation & Copywriting"
        ],

        "music": [
            "Music Department",
            "Content Creation & Copywriting"
        ],

        "design": [
            "Graphic Design & Branding",
            "BSTM Clothing Brand"
        ],

        "trading": [
            "Trading Automation",
            "Data Science & Analytics",
            "Finance & Accounting"
        ],

        "farm": [
            "Micro Farming & Urban Agriculture",
            "Sustainability & Environment"
        ],

        "agriculture": [
            "Micro Farming & Urban Agriculture",
            "Research & Development"
        ],

        "security": [
            "VPN & Network Security",
            "Private Security"
        ]
    }

    for keyword, routes in mapping.items():

        if keyword in text:

            for route in routes:

                if route not in pathways:
                    pathways.append(route)

    if not pathways:

        pathways = [
            "Research & Development",
            "BSTM Tutorial Center"
        ]

    return pathways


# ============================================================
# BUSINESS REGISTRATION
# ============================================================

def register_business():

    print("\n========================================")
    print("BSTM BUSINESS ACTIVATION")
    print("========================================")

    name = input("Business name: ").strip()
    owner = input("Owner/contact: ").strip()
    sector = input("Business sector: ").strip()
    location = input("Location: ").strip()

    problem = input(
        "What is the main problem you want solved? "
    ).strip()

    business_id = uid("B")

    profile = {
        "id": business_id,
        "name": name,
        "owner": owner,
        "sector": sector,
        "location": location,
        "main_problem": problem,

        "audit_status": "Pending",

        "opportunities_generated": 0,

        "created_at": now()
    }

    businesses = load("businesses")

    businesses.append(profile)

    save("businesses", businesses)

    add_node(
        business_id,
        "business",
        name
    )

    print("\nBusiness activated.")
    print("Business ID:", business_id)

    log_event(
        "business_activated",
        {
            "business_id": business_id
        }
    )


# ============================================================
# BUSINESS HEALTH AUDIT
# ============================================================

def business_health_audit():

    businesses = load("businesses")

    if not businesses:
        print("No businesses registered.")
        return

    print("\n=== BUSINESS HEALTH AUDIT ===")

    for b in businesses:

        print(
            f"{b['id']} | "
            f"{b['name']} | "
            f"Audit: {b['audit_status']}"
        )

    business_id = input(
        "\nEnter Business ID: "
    ).strip()

    business = next(
        (
            b for b in businesses
            if b["id"] == business_id
        ),
        None
    )

    if not business:
        print("Business not found.")
        return

    print("\nRate each area from 1 to 10.")

    areas = [
        "Marketing",
        "Sales",
        "Technology",
        "Operations",
        "Inventory",
        "Finance",
        "Logistics",
        "Human Resources",
        "Digital Presence",
        "Data & Analytics"
    ]

    scores = {}

    for area in areas:

        try:
            score = int(
                input(
                    f"{area}: "
                )
            )

            score = max(
                1,
                min(10, score)
            )

        except ValueError:

            score = 1

        scores[area] = score

    audit_id = uid("AUDIT")

    audit = {
        "id": audit_id,
        "business_id": business_id,
        "scores": scores,
        "created_at": now()
    }

    audits = load("audits")

    audits.append(audit)

    save("audits", audits)

    for b in businesses:

        if b["id"] == business_id:

            b["audit_status"] = "Completed"
            b["latest_audit"] = audit_id

    save("businesses", businesses)

    add_node(
        audit_id,
        "audit",
        "Business Health Audit"
    )

    add_edge(
        business_id,
        "received_audit",
        audit_id
    )

    print("\nAudit completed.")

    generate_opportunities_from_audit(
        business_id,
        scores
    )


# ============================================================
# OPPORTUNITY CASCADE ENGINE
# ============================================================

def generate_opportunities_from_audit(
    business_id,
    scores
):

    businesses = load("businesses")

    business = next(
        (
            b for b in businesses
            if b["id"] == business_id
        ),
        None
    )

    if not business:
        return

    recommendations = {

        "Marketing":
            (
                "Digital Marketing & Advertising",
                "Improve customer acquisition and digital marketing."
            ),

        "Sales":
            (
                "Digital Marketing & Advertising",
                "Improve sales conversion and customer acquisition."
            ),

        "Technology":
            (
                "System Integration & API",
                "Improve business technology infrastructure."
            ),

        "Operations":
            (
                "Project Management Office",
                "Improve operational workflows."
            ),

        "Inventory":
            (
                "Finance & Accounting",
                "Implement inventory and financial tracking."
            ),

        "Finance":
            (
                "Finance & Accounting",
                "Improve financial visibility and reporting."
            ),

        "Logistics":
            (
                "CabLink Transportation",
                "Improve transportation and logistics."
            ),

        "Human Resources":
            (
                "Human Resources & Talent Development",
                "Improve recruitment and talent development."
            ),

        "Digital Presence":
            (
                "Web Development",
                "Develop or improve the business digital presence."
            ),

        "Data & Analytics":
            (
                "Data Science & Analytics",
                "Develop dashboards and decision-support systems."
            )
    }

    opportunities = load("opportunities")

    generated = 0

    for area, score in scores.items():

        if score <= 5:

            department, description = recommendations[area]

            opportunity_id = uid("O")

            opportunity = {

                "id": opportunity_id,

                "title":
                    f"{area} Improvement for {business['name']}",

                "source":
                    "Business Health Audit",

                "business_id":
                    business_id,

                "category":
                    area,

                "department":
                    department,

                "description":
                    description,

                "potential_revenue_bwp":
                    None,

                "status":
                    "Open",

                "assigned_to":
                    None,

                "created_at":
                    now()
            }

            opportunities.append(
                opportunity
            )

            add_node(
                opportunity_id,
                "opportunity",
                opportunity["title"]
            )

            add_edge(
                business_id,
                "generated",
                opportunity_id
            )

            generated += 1

    save(
        "opportunities",
        opportunities
    )

    print(
        f"\n{generated} opportunities generated."
    )

    if generated:

        match_opportunities()


# ============================================================
# CAPABILITY REGISTRATION
# ============================================================

def add_capability():

    youth = load("youth")

    if not youth:
        print("No youth registered.")
        return

    print("\n=== ADD CAPABILITY ===")

    for y in youth:
        print(
            y["id"],
            "|",
            y["name"]
        )

    youth_id = input(
        "\nYouth ID: "
    ).strip()

    youth_profile = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not youth_profile:
        print("Youth not found.")
        return

    capability = input(
        "Capability: "
    ).strip()

    try:
        level = int(
            input(
                "Capability level 1-10: "
            )
        )

        level = max(
            1,
            min(10, level)
        )

    except ValueError:

        level = 1

    record = {
        "id": uid("CAP"),
        "youth_id": youth_id,
        "capability": capability,
        "level": level,
        "evidence_count": 0,
        "created_at": now()
    }

    capabilities = load("capabilities")

    capabilities.append(record)

    save(
        "capabilities",
        capabilities
    )

    youth_profile["capabilities"].append(
        capability
    )

    youth_profile["capability_score"] += level

    save(
        "youth",
        youth
    )

    print(
        "\nCapability added."
    )


# ============================================================
# TRIAL ENGINE
# ============================================================

def create_trial():

    print("\n=== CREATE BSTM TRIAL ===")

    title = input(
        "Trial title: "
    ).strip()

    description = input(
        "Trial description: "
    ).strip()

    department = input(
        "Department: "
    ).strip()

    try:

        difficulty = int(
            input(
                "Difficulty 1-10: "
            )
        )

    except ValueError:

        difficulty = 1

    try:

        learning_value = int(
            input(
                "Learning value 1-100: "
            )
        )

    except ValueError:

        learning_value = 50

    try:

        reward = float(
            input(
                "Potential reward BWP: "
            )
        )

    except ValueError:

        reward = 0

    trial_id = uid("T")

    trial = {

        "id":
            trial_id,

        "title":
            title,

        "description":
            description,

        "department":
            department,

        "difficulty":
            difficulty,

        "learning_value":
            learning_value,

        "reward_bwp":
            reward,

        "status":
            "Open",

        "assigned_to":
            None,

        "created_at":
            now()
    }

    trials = load("trials")

    trials.append(
        trial
    )

    save(
        "trials",
        trials
    )

    add_node(
        trial_id,
        "trial",
        title
    )

    print(
        "\nTrial created:",
        trial_id
    )


# ============================================================
# TRIAL COMPLETION
# ============================================================

def complete_trial():

    trials = load("trials")

    if not trials:
        print("No trials available.")
        return

    print("\n=== OPEN TRIALS ===")

    for t in trials:

        if t["status"] == "Open":

            print(
                t["id"],
                "|",
                t["title"],
                "| Reward:",
                t["reward_bwp"]
            )

    trial_id = input(
        "\nTrial ID: "
    ).strip()

    trial = next(
        (
            t for t in trials
            if t["id"] == trial_id
        ),
        None
    )

    if not trial:
        print("Trial not found.")
        return

    youth = load("youth")

    youth_id = input(
        "Youth ID completing trial: "
    ).strip()

    youth_profile = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not youth_profile:
        print("Youth not found.")
        return

    evidence_text = input(
        "Describe evidence submitted: "
    ).strip()

    evidence = {

        "id":
            uid("EVID"),

        "trial_id":
            trial_id,

        "youth_id":
            youth_id,

        "description":
            evidence_text,

        "status":
            "Submitted",

        "created_at":
            now()
    }

    evidence_list = load(
        "evidence"
    )

    evidence_list.append(
        evidence
    )

    save(
        "evidence",
        evidence_list
    )

    trial["status"] = "Completed"
    trial["assigned_to"] = youth_id

    save(
        "trials",
        trials
    )

    youth_profile[
        "completed_trials"
    ] += 1

    youth_profile[
        "learning_score"
    ] += trial[
        "learning_value"
    ]

    youth_profile[
        "revenue"
    ] += trial[
        "reward_bwp"
    ]

    if youth_profile[
        "completed_trials"
    ] >= 1:

        youth_profile[
            "level"
        ] = "Trial Builder"

    if youth_profile[
        "completed_trials"
    ] >= 5:

        youth_profile[
            "level"
        ] = "Contributor"

    if youth_profile[
        "completed_trials"
    ] >= 10:

        youth_profile[
            "level"
        ] = "Service Provider"

    if youth_profile[
        "completed_trials"
    ] >= 25:

        youth_profile[
            "level"
        ] = "Specialist"

    if youth_profile[
        "completed_trials"
    ] >= 50:

        youth_profile[
            "level"
        ] = "Department Member"

    if youth_profile[
        "completed_trials"
    ] >= 100:

        youth_profile[
            "level"
        ] = "Ecosystem Builder"

    save(
        "youth",
        youth
    )

    add_edge(
        youth_id,
        "completed",
        trial_id
    )

    print(
        "\nTrial completed."
    )

    print(
        "New Youth Level:",
        youth_profile["level"]
    )


# ============================================================
# OPPORTUNITY MATCHING ENGINE
# ============================================================

def match_opportunities():

    youth = load("youth")

    opportunities = load(
        "opportunities"
    )

    matches = load(
        "matches"
    )

    print(
        "\n=== OPPORTUNITY MATCHING ENGINE ==="
    )

    for opportunity in opportunities:

        if opportunity[
            "status"
        ] != "Open":

            continue

        department = (
            opportunity.get(
                "department",
                ""
            )
        ).lower()

        for person in youth:

            pathways = [
                p.lower()
                for p in person.get(
                    "recommended_pathways",
                    []
                )
            ]

            score = 0

            for pathway in pathways:

                if (
                    department
                    in pathway
                ):

                    score += 50

            if score == 0:
                continue

            score += min(
                person.get(
                    "completed_trials",
                    0
                ) * 2,
                20
            )

            score += min(
                person.get(
                    "capability_score",
                    0
                ),
                20
            )

            match = {

                "id":
                    uid("MATCH"),

                "opportunity_id":
                    opportunity["id"],

                "youth_id":
                    person["id"],

                "score":
                    score,

                "status":
                    "Recommended",

                "created_at":
                    now()
            }

            matches.append(
                match
            )

            print(
                f"{person['name']} "
                f"→ "
                f"{opportunity['title']} "
                f""
                f"(Score: {score})"
            )

    save(
        "matches",
        matches
    )


# ============================================================
# OPPORTUNITY CASCADE ANALYSIS
# ============================================================

def analyze_cascade():

    opportunities = load(
        "opportunities"
    )

    print(
        "\n=== OPPORTUNITY CASCADE ANALYSIS ==="
    )

    cascade_map = {

        "Web Development":
            [
                "Digital Marketing",
                "Analytics",
                "Automation"
            ],

        "Digital Marketing & Advertising":
            [
                "Content Creation",
                "Social Media",
                "Analytics"
            ],

        "Finance & Accounting":
            [
                "Data Analytics",
                "Business Intelligence",
                "Automation"
            ],

        "CabLink Transportation":
            [
                "Logistics Optimization",
                "Marketplace Integration"
            ],

        "System Integration & API":
            [
                "Automation",
                "AI",
                "Data Synchronization"
            ]
    }

    for opportunity in opportunities:

        department = opportunity.get(
            "department",
            ""
        )

        if department in cascade_map:

            print(
                "\nOpportunity:",
                opportunity["title"]
            )

            print(
                "Potential next opportunities:"
            )

            for next_opportunity in cascade_map[
                department
            ]:

                print(
                    " →",
                    next_opportunity
                )


# ============================================================
# ECOSYSTEM HEALTH
# ============================================================

def ecosystem_health():

    youth = load("youth")
    businesses = load("businesses")
    opportunities = load("opportunities")
    trials = load("trials")
    matches = load("matches")

    print(
        "\n========================================"
    )

    print(
        "BSTM ECOSYSTEM HEALTH INDEX"
    )

    print(
        "========================================"
    )

    youth_score = min(
        len(youth) * 10,
        100
    )

    business_score = min(
        len(businesses) * 10,
        100
    )

    opportunity_score = min(
        len(opportunities) * 5,
        100
    )

    trial_score = min(
        len(trials) * 5,
        100
    )

    matching_score = min(
        len(matches) * 5,
        100
    )

    scores = {

        "Youth Activation":
            youth_score,

        "Business Engagement":
            business_score,

        "Opportunity Flow":
            opportunity_score,

        "Trial Activity":
            trial_score,

        "Opportunity Matching":
            matching_score
    }

    for name, score in scores.items():

        print(
            f"{name}: {score}%"
        )

    if opportunities and not matches:

        print(
            "\nBOTTLENECK DETECTED:"
        )

        print(
            "Opportunities exist, "
            "but matching activity is low."
        )

    if youth and not opportunities:

        print(
            "\nBOTTLENECK DETECTED:"
        )

        print(
            "Youth are entering the ecosystem "
            "faster than opportunities are being generated."
        )


# ============================================================
# SYSTEM STATUS
# ============================================================

def system_status():

    print(
        "\n========================================"
    )

    print(
        "BSTM ACTIVATION ENGINE v2"
    )

    print(
        "========================================"
    )

    for key in [
        "youth",
        "businesses",
        "opportunities",
        "trials",
        "capabilities",
        "matches",
        "audits",
        "evidence"
    ]:

        print(
            key.capitalize() + ":",
            len(load(key))
        )

    youth = load(
        "youth"
    )

    revenue = sum(
        float(
            y.get(
                "revenue",
                0
            ) or 0
        )
        for y in youth
    )

    print(
        "Tracked Youth Revenue:",
        revenue,
        "BWP"
    )

    graph = load(
        "graph"
    )

    print(
        "Graph Nodes:",
        len(
            graph["nodes"]
        )
    )

    print(
        "Graph Relationships:",
        len(
            graph["edges"]
        )
    )


# ============================================================
# MAIN MENU
# ============================================================

def menu():

    ensure_data()

    initialize_departments()

    while True:

        print(
            """
==================================================
 BSTM ACTIVATION ENGINE v2
 ADAPTIVE ECOSYSTEM OPERATING LAYER
==================================================

1.  Activate Youth
2. Activate Business
3. Add Youth Capability
4. Create Trial
5. Complete Trial
6. Business Health Audit
7. Run Opportunity Matching
8. Analyze Opportunity Cascade
9. View Ecosystem Health
10. System Status
11. Exit

==================================================
"""
        )

        choice = input(
            "BSTM > "
        ).strip()

        if choice == "1":

            register_youth()

        elif choice == "2":

            register_business()

        elif choice == "3":

            add_capability()

        elif choice == "4":

            create_trial()

        elif choice == "5":

            complete_trial()

        elif choice == "6":

            business_health_audit()

        elif choice == "7":

            match_opportunities()

        elif choice == "8":

            analyze_cascade()

        elif choice == "9":

            ecosystem_health()

        elif choice == "10":

            system_status()

        elif choice == "11":

            print(
                "\nBSTM Activation Engine shutting down."
            )

            break

        else:

            print(
                "\nInvalid option."
            )


if __name__ == "__main__":

    menu()

