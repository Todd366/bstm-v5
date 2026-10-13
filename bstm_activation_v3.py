#!/usr/bin/env python3

import json
import os
import uuid
import math
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
    "graph": "data/graph.json",
    "assessments": "data/assessments.json",
    "skill_gaps": "data/skill_gaps.json",
    "reputation": "data/reputation.json",
    "recommendations": "data/recommendations.json",
    "transactions": "data/transactions.json"
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
    "graph": {"nodes": [], "edges": []},
    "assessments": [],
    "skill_gaps": [],
    "reputation": [],
    "recommendations": [],
    "transactions": []
}

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

# ------------------------------------------------------------
# CORE
# ------------------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return f"{prefix}-{str(uuid.uuid4())[:8]}"


def save(key, data):
    with open(FILES[key], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load(key):
    try:
        with open(FILES[key], "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULTS[key]


def ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    for key, path in FILES.items():
        if not os.path.exists(path):
            save(key, DEFAULTS[key])


def log_event(event, details):
    activity = load("activity")

    activity.append({
        "id": uid("EV"),
        "timestamp": now(),
        "event": event,
        "details": details
    })

    save("activity", activity)


# ------------------------------------------------------------
# GRAPH
# ------------------------------------------------------------

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

    graph["edges"].append({
        "id": uid("EDGE"),
        "source": source,
        "relation": relation,
        "target": target,
        "metadata": metadata or {},
        "created_at": now()
    })

    save("graph", graph)


# ------------------------------------------------------------
# DEPARTMENT KNOWLEDGE
# ------------------------------------------------------------

DEPARTMENT_KEYWORDS = {

    "AI & Machine Learning":
        ["ai", "machine learning", "artificial intelligence",
         "python", "automation", "agents"],

    "Trading Automation":
        ["trading", "forex", "stocks", "crypto",
         "technical analysis", "mt4", "mt5"],

    "VPN & Network Security":
        ["security", "cybersecurity", "network",
         "vpn", "privacy", "hacking"],

    "Web Development":
        ["web", "website", "html", "css", "javascript",
         "frontend", "backend", "full stack"],

    "Mobile Application Development":
        ["mobile", "android", "ios", "app", "flutter"],

    "System Integration & API":
        ["api", "integration", "systems", "backend",
         "database", "architecture"],

    "Data Science & Analytics":
        ["data", "analytics", "statistics",
         "dashboard", "research", "excel"],

    "Blockchain & Cryptocurrency":
        ["blockchain", "crypto", "web3",
         "bitcoin", "token"],

    "Graphic Design & Branding":
        ["design", "graphics", "logo", "branding",
         "photoshop", "illustrator"],

    "Content Creation & Copywriting":
        ["writing", "content", "copywriting",
         "blog", "storytelling"],

    "Social Media Management":
        ["social media", "facebook", "tiktok",
         "instagram", "community"],

    "Digital Marketing & Advertising":
        ["marketing", "advertising", "sales",
         "seo", "campaigns"],

    "Music Department":
        ["music", "singing", "production",
         "beats", "audio"],

    "CabLink Transportation":
        ["driving", "transport", "logistics",
         "delivery", "taxi"],

    "Finance & Accounting":
        ["finance", "accounting", "money",
         "bookkeeping", "budget"],

    "Marketplace & E-Commerce":
        ["ecommerce", "marketplace", "selling",
         "online store", "retail"],

    "Research & Development":
        ["research", "innovation", "science",
         "experiments", "invention"],

    "Micro Farming & Urban Agriculture":
        ["farming", "agriculture", "farm",
         "food", "plants"],

    "Sustainability & Environment":
        ["environment", "sustainability",
         "recycling", "green"],

    "Human Resources & Talent Development":
        ["people", "hr", "recruitment",
         "leadership", "training"],

    "Project Management Office":
        ["management", "projects", "planning",
         "coordination", "execution"]
}


def initialize_departments():
    departments = load("departments")

    existing = {d["name"] for d in departments}

    for name in DEPARTMENTS:
        if name not in existing:

            d = {
                "id": uid("D"),
                "name": name,
                "status": "Active",
                "created_at": now()
            }

            departments.append(d)

            add_node(
                d["id"],
                "department",
                name
            )

    save("departments", departments)


# ------------------------------------------------------------
# TEXT INTELLIGENCE
# ------------------------------------------------------------

def tokenize(text):
    return set(
        word.strip(".,!?;:()[]{}").lower()
        for word in text.split()
        if len(word.strip()) > 2
    )


def keyword_score(text, keywords):
    tokens = tokenize(text)

    score = 0

    for keyword in keywords:

        key_tokens = tokenize(keyword)

        if keyword.lower() in text.lower():
            score += 3

        elif key_tokens & tokens:
            score += 1

    return score


# ------------------------------------------------------------
# YOUTH ASSESSMENT
# ------------------------------------------------------------

def activate_youth():

    print("\n==========================================")
    print("BSTM ADAPTIVE YOUTH ACTIVATION")
    print("==========================================")

    name = input("Name: ").strip()
    location = input("Location: ").strip()

    passion = input(
        "What are you passionate about? "
    ).strip()

    skills = input(
        "What skills do you currently have? "
    ).strip()

    goal = input(
        "What do you want to achieve? "
    ).strip()

    experience = input(
        "Describe your previous experience: "
    ).strip()

    availability = input(
        "How many hours per week can you commit? "
    ).strip()

    equipment = input(
        "What equipment/resources do you have? "
    ).strip()

    learning_style = input(
        "How do you learn best? "
        "(video/practice/reading/mentor): "
    ).strip()

    youth_id = uid("Y")

    profile = {
        "id": youth_id,
        "name": name,
        "location": location,
        "passion": passion,
        "skills": skills,
        "goal": goal,
        "experience": experience,
        "availability": availability,
        "equipment": equipment,
        "learning_style": learning_style,

        "level": "Explorer",

        "capability_score": 0,
        "learning_score": 0,
        "reputation_score": 0,
        "reliability_score": 50,

        "completed_trials": 0,
        "completed_opportunities": 0,

        "revenue": 0,

        "capabilities": [],
        "recommended_pathways": [],
        "skill_gaps": [],

        "created_at": now()
    }

    youth = load("youth")
    youth.append(profile)
    save("youth", youth)

    add_node(
        youth_id,
        "youth",
        name
    )

    text = " ".join([
        passion,
        skills,
        goal,
        experience
    ]).lower()

    pathway_scores = {}

    for department, keywords in DEPARTMENT_KEYWORDS.items():

        score = keyword_score(
            text,
            keywords
        )

        if score > 0:
            pathway_scores[
                department
            ] = score

    if not pathway_scores:

        pathway_scores = {
            "Research & Development": 1,
            "BSTM Tutorial Center": 1
        }

    ranked = sorted(
        pathway_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    pathways = [
        department
        for department, score in ranked[:5]
    ]

    assessment = {

        "id": uid("ASSESS"),

        "youth_id": youth_id,

        "pathway_scores":
            pathway_scores,

        "recommended_pathways":
            pathways,

        "created_at":
            now()
    }

    assessments = load(
        "assessments"
    )

    assessments.append(
        assessment
    )

    save(
        "assessments",
        assessments
    )

    for y in youth:

        if y["id"] == youth_id:

            y[
                "recommended_pathways"
            ] = pathways

    save(
        "youth",
        youth
    )

    log_event(
        "adaptive_youth_activation",
        {
            "youth_id":
                youth_id,

            "pathways":
                pathways
        }
    )

    print("\n==========================================")
    print("YOUTH ACTIVATED")
    print("==========================================")

    print(
        "Activation ID:",
        youth_id
    )

    print("\nAI-Generated Pathways:")

    for i, pathway in enumerate(
        pathways,
        1
    ):

        print(
            f"{i}. {pathway}"
        )

    print(
        "\nNext step: Run Skill Gap Analysis."
    )


# ------------------------------------------------------------
# SKILL GAP ENGINE
# ------------------------------------------------------------

def analyze_skill_gaps():

    youth = load("youth")

    if not youth:

        print(
            "No youth registered."
        )

        return

    for y in youth:

        print(
            y["id"],
            "|",
            y["name"],
            "|",
            y.get(
                "level",
                "Explorer"
            )
        )

    youth_id = input(
        "\nYouth ID: "
    ).strip()

    person = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not person:

        print(
            "Youth not found."
        )

        return

    capabilities = load(
        "capabilities"
    )

    owned = {

        c["capability"].lower()

        for c in capabilities

        if c["youth_id"]
        == youth_id
    }

    pathway = person.get(
        "recommended_pathways",
        []
    )

    required = {

        "Web Development":
            [
                "HTML",
                "CSS",
                "JavaScript",
                "Git"
            ],

        "AI & Machine Learning":
            [
                "Python",
                "Data",
                "Machine Learning",
                "AI"
            ],

        "Digital Marketing & Advertising":
            [
                "Marketing",
                "Copywriting",
                "Analytics",
                "Advertising"
            ],

        "Data Science & Analytics":
            [
                "Excel",
                "Statistics",
                "Data Analysis",
                "Visualization"
            ],

        "Trading Automation":
            [
                "Trading",
                "Risk Management",
                "Technical Analysis",
                "Programming"
            ],

        "Graphic Design & Branding":
            [
                "Graphic Design",
                "Branding",
                "Typography"
            ],

        "Music Department":
            [
                "Music Production",
                "Audio",
                "Composition"
            ]
    }

    gaps = []

    for department in pathway:

        for skill in required.get(
            department,
            []
        ):

            if skill.lower() not in owned:

                gaps.append({
                    "department":
                        department,

                    "skill":
                        skill,

                    "priority":
                        1
                })

    skill_gaps = load(
        "skill_gaps"
    )

    record = {

        "id":
            uid("GAP"),

        "youth_id":
            youth_id,

        "gaps":
            gaps,

        "created_at":
            now()
    }

    skill_gaps.append(
        record
    )

    save(
        "skill_gaps",
        skill_gaps
    )

    person[
        "skill_gaps"
    ] = gaps

    save(
        "youth",
        youth
    )

    print(
        "\n=== SKILL GAP ANALYSIS ==="
    )

    if not gaps:

        print(
            "No major skill gaps detected."
        )

    else:

        for gap in gaps:

            print(
                f"[{gap['department']}] "
                f"{gap['skill']}"
            )


# ------------------------------------------------------------
# CAPABILITY
# ------------------------------------------------------------

def add_capability():

    youth = load("youth")

    if not youth:

        print(
            "No youth registered."
        )

        return

    for y in youth:

        print(
            y["id"],
            "|",
            y["name"]
        )

    youth_id = input(
        "\nYouth ID: "
    ).strip()

    person = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not person:

        print(
            "Youth not found."
        )

        return

    capability = input(
        "Capability name: "
    ).strip()

    try:

        level = int(
            input(
                "Current capability level 1-10: "
            )
        )

        level = max(
            1,
            min(
                10,
                level
            )
        )

    except ValueError:

        level = 1

    evidence = input(
        "Evidence of capability: "
    ).strip()

    record = {

        "id":
            uid("CAP"),

        "youth_id":
            youth_id,

        "capability":
            capability,

        "level":
            level,

        "evidence":
            evidence,

        "evidence_count":
            1,

        "verified":
            False,

        "created_at":
            now()
    }

    capabilities = load(
        "capabilities"
    )

    capabilities.append(
        record
    )

    save(
        "capabilities",
        capabilities
    )

    person[
        "capabilities"
    ].append(
        capability
    )

    person[
        "capability_score"
    ] += level

    save(
        "youth",
        youth
    )

    add_edge(
        youth_id,
        "has_capability",
        record["id"]
    )

    print(
        "\nCapability registered."
    )


# ------------------------------------------------------------
# TRIAL GENERATOR
# ------------------------------------------------------------

def generate_personalized_trial():

    youth = load("youth")

    if not youth:

        print(
            "No youth registered."
        )

        return

    for y in youth:

        print(
            y["id"],
            "|",
            y["name"],
            "| Level:",
            y.get(
                "level",
                "Explorer"
            )
        )

    youth_id = input(
        "\nYouth ID: "
    ).strip()

    person = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not person:

        print(
            "Youth not found."
        )

        return

    pathways = person.get(
        "recommended_pathways",
        []
    )

    gaps = person.get(
        "skill_gaps",
        []
    )

    if gaps:

        target = gaps[0]["skill"]

        department = gaps[0][
            "department"
        ]

    elif pathways:

        department = pathways[0]

        target = "Foundational " + department

    else:

        department = (
            "Research & Development"
        )

        target = (
            "General Problem Solving"
        )

    completed = person.get(
        "completed_trials",
        0
    )

    difficulty = min(
        10,
        1 + completed // 10
    )

    reward = 50 + (
        difficulty * 25
    )

    trial = {

        "id":
            uid("T"),

        "title":
            f"Personalized Trial: {target}",

        "description":
            (
                f"Complete a practical "
                f"real-world task focused "
                f"on {target}."
            ),

        "department":
            department,

        "target_skill":
            target,

        "difficulty":
            difficulty,

        "learning_value":
            100 - (
                difficulty * 3
            ),

        "reward_bwp":
            reward,

        "recommended_for":
            youth_id,

        "status":
            "Open",

        "created_at":
            now()
    }

    trials = load(
        "trials"
    )

    trials.append(
        trial
    )

    save(
        "trials",
        trials
    )

    add_node(
        trial["id"],
        "trial",
        trial["title"]
    )

    add_edge(
        youth_id,
        "recommended_trial",
        trial["id"]
    )

    print(
        "\n=========================================="
    )

    print(
        "PERSONALIZED TRIAL GENERATED"
    )

    print(
        "=========================================="
    )

    print(
        "Trial:",
        trial["id"]
    )

    print(
        "Department:",
        department
    )

    print(
        "Target Skill:",
        target
    )

    print(
        "Difficulty:",
        difficulty
    )

    print(
        "Reward:",
        reward,
        "BWP"
    )


# ------------------------------------------------------------
# BUSINESS
# ------------------------------------------------------------

def register_business():

    print(
        "\n=== BSTM BUSINESS ACTIVATION ==="
    )

    name = input(
        "Business name: "
    ).strip()

    owner = input(
        "Owner/contact: "
    ).strip()

    sector = input(
        "Sector: "
    ).strip()

    location = input(
        "Location: "
    ).strip()

    problem = input(
        "Main problem: "
    ).strip()

    business_id = uid("B")

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
        name
    )

    print(
        "\nBusiness activated."
    )

    print(
        "Business ID:",
        business_id
    )


# ------------------------------------------------------------
# BUSINESS AUDIT
# ------------------------------------------------------------

def business_health_audit():

    businesses = load(
        "businesses"
    )

    if not businesses:

        print(
            "No businesses registered."
        )

        return

    for b in businesses:

        print(
            b["id"],
            "|",
            b["name"]
        )

    business_id = input(
        "\nBusiness ID: "
    ).strip()

    business = next(
        (
            b for b in businesses
            if b["id"] == business_id
        ),
        None
    )

    if not business:

        print(
            "Business not found."
        )

        return

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

    print(
        "\nRate each area 1-10."
    )

    for area in areas:

        try:

            score = int(
                input(
                    area + ": "
                )
            )

            score = max(
                1,
                min(
                    10,
                    score
                )
            )

        except ValueError:

            score = 1

        scores[
            area
        ] = score

    audit_id = uid(
        "AUDIT"
    )

    audit = {

        "id":
            audit_id,

        "business_id":
            business_id,

        "scores":
            scores,

        "created_at":
            now()
    }

    audits = load(
        "audits"
    )

    audits.append(
        audit
    )

    save(
        "audits",
        audits
    )

    business[
        "audit_status"
    ] = "Completed"

    business[
        "latest_audit"
    ] = audit_id

    save(
        "businesses",
        businesses
    )

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

    generate_opportunities(
        business_id,
        scores
    )


# ------------------------------------------------------------
# OPPORTUNITY GENERATION
# ------------------------------------------------------------

AREA_ROUTING = {

    "Marketing":
        "Digital Marketing & Advertising",

    "Sales":
        "Digital Marketing & Advertising",

    "Technology":
        "System Integration & API",

    "Operations":
        "Project Management Office",

    "Inventory":
        "Finance & Accounting",

    "Finance":
        "Finance & Accounting",

    "Logistics":
        "CabLink Transportation",

    "Human Resources":
        "Human Resources & Talent Development",

    "Digital Presence":
        "Web Development",

    "Data & Analytics":
        "Data Science & Analytics"
}


def generate_opportunities(
    business_id,
    scores
):

    businesses = load(
        "businesses"
    )

    business = next(
        (
            b for b in businesses
            if b["id"] == business_id
        ),
        None
    )

    if not business:

        return

    opportunities = load(
        "opportunities"
    )

    generated = 0

    for area, score in scores.items():

        if score > 5:

            continue

        department = AREA_ROUTING.get(
            area,
            "Research & Development"
        )

        priority = 11 - score

        opportunity = {

            "id":
                uid("O"),

            "title":
                f"{area} Transformation",

            "source":
                "Business Health Audit",

            "business_id":
                business_id,

            "category":
                area,

            "department":
                department,

            "priority":
                priority,

            "description":
                (
                    f"Improve {area} "
                    f"performance for "
                    f"{business['name']}."
                ),

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
            opportunity["id"],
            "opportunity",
            opportunity["title"]
        )

        add_edge(
            business_id,
            "generated",
            opportunity["id"]
        )

        generated += 1

    save(
        "opportunities",
        opportunities
    )

    business[
        "opportunities_generated"
    ] = generated

    save(
        "businesses",
        businesses
    )

    print(
        "\nGenerated",
        generated,
        "opportunities."
    )


# ------------------------------------------------------------
# ADVANCED MATCHING ENGINE
# ------------------------------------------------------------

def run_matching():

    youth = load(
        "youth"
    )

    opportunities = load(
        "opportunities"
    )

    matches = []

    print(
        "\n=== BSTM INTELLIGENT MATCHING ENGINE ==="
    )

    for opportunity in opportunities:

        if opportunity.get(
            "status"
        ) != "Open":

            continue

        department = opportunity.get(
            "department",
            ""
        )

        for person in youth:

            score = 0

            pathways = person.get(
                "recommended_pathways",
                []
            )

            capabilities = person.get(
                "capabilities",
                []
            )

            if department in pathways:

                score += 40

            for capability in capabilities:

                if keyword_score(
                    capability,
                    DEPARTMENT_KEYWORDS.get(
                        department,
                        []
                    )
                ):

                    score += 15

            score += min(
                person.get(
                    "capability_score",
                    0
                ),
                20
            )

            score += min(
                person.get(
                    "reliability_score",
                    50
                ) / 5,
                10
            )

            score += min(
                person.get(
                    "completed_trials",
                    0
                ),
                10
            )

            if score <= 0:

                continue

            match = {

                "id":
                    uid("MATCH"),

                "opportunity_id":
                    opportunity["id"],

                "youth_id":
                    person["id"],

                "score":
                    round(
                        score,
                        2
                    ),

                "status":
                    "Recommended",

                "created_at":
                    now()
            }

            matches.append(
                match
            )

    save(
        "matches",
        matches
    )

    print(
        "\nMatches generated:",
        len(matches)
    )

    ranked = sorted(
        matches,
        key=lambda x:
            x["score"],
        reverse=True
    )

    for match in ranked[:20]:

        person = next(
            (
                y for y in youth
                if y["id"]
                == match["youth_id"]
            ),
            None
        )

        opportunity = next(
            (
                o for o in opportunities
                if o["id"]
                == match[
                    "opportunity_id"
                ]
            ),
            None
        )

        if person and opportunity:

            print(
                f"\n{person['name']}"
            )

            print(
                "→",
                opportunity[
                    "title"
                ]
            )

            print(
                "Score:",
                match[
                    "score"
                ]
            )


# ------------------------------------------------------------
# TRIAL COMPLETION
# ------------------------------------------------------------

def complete_trial():

    trials = load(
        "trials"
    )

    open_trials = [

        t for t in trials

        if t.get(
            "status"
        ) == "Open"
    ]

    if not open_trials:

        print(
            "No open trials."
        )

        return

    for t in open_trials:

        print(
            t["id"],
            "|",
            t["title"],
            "| Reward:",
            t.get(
                "reward_bwp",
                0
            )
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

        print(
            "Trial not found."
        )

        return

    youth = load(
        "youth"
    )

    youth_id = input(
        "Youth ID: "
    ).strip()

    person = next(
        (
            y for y in youth
            if y["id"] == youth_id
        ),
        None
    )

    if not person:

        print(
            "Youth not found."
        )

        return

    evidence_text = input(
        "Evidence submitted: "
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

    trial[
        "status"
    ] = "Completed"

    trial[
        "assigned_to"
    ] = youth_id

    save(
        "trials",
        trials
    )

    person[
        "completed_trials"
    ] += 1

    person[
        "learning_score"
    ] += trial.get(
        "learning_value",
        50
    )

    person[
        "revenue"
    ] += float(
        trial.get(
            "reward_bwp",
            0
        ) or 0
    )

    # Dynamic progression
    count = person[
        "completed_trials"
    ]

    if count >= 1:
        person["level"] = "Trial Builder"

    if count >= 5:
        person["level"] = "Contributor"

    if count >= 10:
        person["level"] = "Service Provider"

    if count >= 25:
        person["level"] = "Specialist"

    if count >= 50:
        person["level"] = "Department Member"

    if count >= 75:
        person["level"] = "Team Leader"

    if count >= 100:
        person["level"] = "Ecosystem Builder"

    save(
        "youth",
        youth
    )

    add_edge(
        youth_id,
        "completed_trial",
        trial_id
    )

    log_event(
        "trial_completed",
        {
            "youth_id":
                youth_id,

            "trial_id":
                trial_id
        }
    )

    print(
        "\nTrial completed."
    )

    print(
        "New level:",
        person["level"]
    )

    print(
        "Total trials:",
        count
    )


# ------------------------------------------------------------
# REPUTATION ENGINE
# ------------------------------------------------------------

def calculate_reputation():

    youth = load(
        "youth"
    )

    evidence = load(
        "evidence"
    )

    for person in youth:

        completed = person.get(
            "completed_trials",
            0
        )

        opportunities = person.get(
            "completed_opportunities",
            0
        )

        reliability = person.get(
            "reliability_score",
            50
        )

        evidence_count = len([

            e for e in evidence

            if e[
                "youth_id"
            ]
            == person["id"]

        ])

        score = (

            completed * 2

            + opportunities * 5

            + evidence_count * 2

            + reliability

        )

        score = min(
            100,
            score
        )

        person[
            "reputation_score"
        ] = round(
            score,
            2
        )

    save(
        "youth",
        youth
    )

    print(
        "\nReputation engine updated."
    )

    for person in youth:

        print(
            person["name"],
            "→",
            person[
                "reputation_score"
            ]
        )


# ------------------------------------------------------------
# 100 TRIALS DASHBOARD
# ------------------------------------------------------------

def trials_dashboard():

    youth = load(
        "youth"
    )

    print(
        "\n=== BSTM 100 TRIALS DASHBOARD ==="
    )

    for person in youth:

        count = person.get(
            "completed_trials",
            0
        )

        progress = min(
            100,
            count
        )

        bars = int(
            progress / 5
        )

        print(
            f"\n{person['name']}"
        )

        print(
            "[" +
            "#" * bars +
            "-" * (
                20 - bars
            ) +
            "]",
            f"{progress}%"
        )

        print(
            "Trials:",
            count,
            "/ 100"
        )

        print(
            "Level:",
            person.get(
                "level",
                "Explorer"
            )
        )

        print(
            "Reputation:",
            person.get(
                "reputation_score",
                0
            )
        )


# ------------------------------------------------------------
# ECOSYSTEM INTELLIGENCE
# ------------------------------------------------------------

def ecosystem_intelligence():

    youth = load(
        "youth"
    )

    businesses = load(
        "businesses"
    )

    opportunities = load(
        "opportunities"
    )

    trials = load(
        "trials"
    )

    matches = load(
        "matches"
    )

    graph = load(
        "graph"
    )

    print(
        "\n=========================================="
    )

    print(
        "BSTM ECOSYSTEM INTELLIGENCE"
    )

    print(
        "=========================================="
    )

    metrics = {

        "Youth":
            len(youth),

        "Businesses":
            len(businesses),

        "Open Opportunities":
            len([
                o for o in opportunities
                if o.get(
                    "status"
                ) == "Open"
            ]),

        "Trials":
            len(trials),

        "Matches":
            len(matches),

        "Graph Nodes":
            len(
                graph["nodes"]
            ),

        "Graph Edges":
            len(
                graph["edges"]
            )
    }

    for key, value in metrics.items():

        print(
            f"{key}: {value}"
        )

    print(
        "\n--- BOTTLENECK ANALYSIS ---"
    )

    if youth and not businesses:

        print(
            "⚠ Youth activation exists "
            "but business demand is low."
        )

    if businesses and not opportunities:

        print(
            "⚠ Businesses exist "
            "but opportunity generation is low."
        )

    if opportunities and not matches:

        print(
            "⚠ Opportunities exist "
            "but matching is inactive."
        )

    if matches:

        print(
            "✓ Opportunity matching active."
        )

    if trials:

        print(
            "✓ Trial engine active."
        )

    print(
        "\n--- SYSTEM LOOP ---"
    )

    print(
        "People → Capability → Trials "
        "→ Evidence → Reputation"
    )

    print(
        "Businesses → Diagnosis → "
        "Opportunities → Matching"
    )

    print(
        "Opportunities → Execution → "
        "Revenue → Learning"
    )

    print(
        "All activity → Graph → "
        "ELOS Intelligence"
    )


# ------------------------------------------------------------
# MENU
# ------------------------------------------------------------

def menu():

    ensure_data()

    initialize_departments()

    while True:

        print(
            """
==================================================
 BSTM ACTIVATION ENGINE V3
 ADAPTIVE INTELLIGENCE CORE
==================================================

1.  Activate Youth
2.  Activate Business
3.  Analyze Youth Skill Gaps
4.  Add Youth Capability
5.  Generate Personalized Trial
6.  Complete Trial
7.  Business Health Audit
8.  Run Intelligent Matching
9.  Update Reputation
10.  100 Trials Dashboard
11. Ecosystem Intelligence
12. Exit

==================================================
"""
        )

        choice = input(
            "BSTM > "
        ).strip()

        if choice == "1":

            activate_youth()

        elif choice == "2":

            register_business()

        elif choice == "3":

            analyze_skill_gaps()

        elif choice == "4":

            add_capability()

        elif choice == "5":

            generate_personalized_trial()

        elif choice == "6":

            complete_trial()

        elif choice == "7":

            business_health_audit()

        elif choice == "8":

            run_matching()

        elif choice == "9":

            calculate_reputation()

        elif choice == "10":

            trials_dashboard()

        elif choice == "11":

            ecosystem_intelligence()

        elif choice == "12":

            print(
                "\nBSTM V3 shutting down."
            )

            break

        else:

            print(
                "\nInvalid option."
            )


if __name__ == "__main__":

    menu()

