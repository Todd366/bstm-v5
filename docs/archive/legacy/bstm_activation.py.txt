#!/usr/bin/env python3

import json
import os
import uuid
from datetime import datetime

DATA_DIR = "data"

FILES = {
    "youth": "data/youth.json",
    "businesses": "data/businesses.json",
    "opportunities": "data/opportunities.json",
    "trials": "data/trials.json",
    "departments": "data/departments.json",
    "activity": "data/activity.json"
}


def now():
    return datetime.utcnow().isoformat() + "Z"


def ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)

    defaults = {
        "youth": [],
        "businesses": [],
        "opportunities": [],
        "trials": [],
        "departments": [],
        "activity": []
    }

    for key, path in FILES.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(defaults[key], f, indent=2)


def load(key):
    with open(FILES[key], "r", encoding="utf-8") as f:
        return json.load(f)


def save(key, data):
    with open(FILES[key], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_event(event_type, details):
    activity = load("activity")

    activity.append({
        "id": str(uuid.uuid4()),
        "timestamp": now(),
        "event": event_type,
        "details": details
    })

    save("activity", activity)


def register_youth():
    print("\n=== BSTM YOUTH ACTIVATION ===")

    name = input("Name: ").strip()
    location = input("Location: ").strip()
    passion = input("What are you passionate about? ").strip()
    skills = input("What skills do you already have? ").strip()
    goal = input("What do you want to achieve? ").strip()

    youth = load("youth")

    profile = {
        "id": "Y-" + str(uuid.uuid4())[:8],
        "name": name,
        "location": location,
        "passion": passion,
        "skills": skills,
        "goal": goal,
        "level": "Explorer",
        "completed_trials": 0,
        "revenue": 0,
        "reputation": 0,
        "capabilities": [],
        "created_at": now()
    }

    youth.append(profile)
    save("youth", youth)

    log_event(
        "youth_registered",
        {"youth_id": profile["id"], "name": name}
    )

    print("\nYouth successfully registered.")
    print("Activation ID:", profile["id"])
    print("Current Level: Explorer")


def register_business():
    print("\n=== BSTM BUSINESS ACTIVATION ===")

    name = input("Business name: ").strip()
    owner = input("Owner/contact: ").strip()
    sector = input("Business sector: ").strip()
    location = input("Location: ").strip()
    problem = input("What is the main problem you want solved? ").strip()

    businesses = load("businesses")

    profile = {
        "id": "B-" + str(uuid.uuid4())[:8],
        "name": name,
        "owner": owner,
        "sector": sector,
        "location": location,
        "main_problem": problem,
        "audit_status": "Pending",
        "opportunities_generated": 0,
        "created_at": now()
    }

    businesses.append(profile)
    save("businesses", businesses)

    log_event(
        "business_registered",
        {"business_id": profile["id"], "name": name}
    )

    print("\nBusiness successfully registered.")
    print("Business ID:", profile["id"])
    print("Next step: Business Health Audit")


def create_trial():
    print("\n=== CREATE BSTM TRIAL ===")

    title = input("Trial title: ").strip()
    description = input("Trial description: ").strip()
    department = input("Department: ").strip()
    reward = input("Potential reward (BWP): ").strip()

    trials = load("trials")

    trial = {
        "id": "T-" + str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "department": department,
        "reward_bwp": reward,
        "status": "Open",
        "created_at": now()
    }

    trials.append(trial)
    save("trials", trials)

    log_event(
        "trial_created",
        {"trial_id": trial["id"], "title": title}
    )

    print("\nTrial created:", trial["id"])


def create_opportunity():
    print("\n=== CREATE OPPORTUNITY ===")

    title = input("Opportunity title: ").strip()
    source = input("Source (business / BSTM / community): ").strip()
    category = input("Category: ").strip()
    description = input("Description: ").strip()
    reward = input("Potential revenue (BWP): ").strip()

    opportunities = load("opportunities")

    opportunity = {
        "id": "O-" + str(uuid.uuid4())[:8],
        "title": title,
        "source": source,
        "category": category,
        "description": description,
        "potential_revenue_bwp": reward,
        "status": "Open",
        "assigned_to": None,
        "created_at": now()
    }

    opportunities.append(opportunity)
    save("opportunities", opportunities)

    log_event(
        "opportunity_created",
        {"opportunity_id": opportunity["id"]}
    )

    print("\nOpportunity created:", opportunity["id"])


def view_youth():
    youth = load("youth")

    print("\n=== BSTM YOUTH ===")

    if not youth:
        print("No youth registered.")
        return

    for y in youth:
        print("\nID:", y["id"])
        print("Name:", y["name"])
        print("Passion:", y["passion"])
        print("Skills:", y["skills"])
        print("Level:", y["level"])
        print("Trials:", y["completed_trials"])
        print("Revenue:", y["revenue"], "BWP")


def view_businesses():
    businesses = load("businesses")

    print("\n=== BSTM BUSINESSES ===")

    if not businesses:
        print("No businesses registered.")
        return

    for b in businesses:
        print("\nID:", b["id"])
        print("Business:", b["name"])
        print("Sector:", b["sector"])
        print("Problem:", b["main_problem"])
        print("Audit:", b["audit_status"])


def view_opportunities():
    opportunities = load("opportunities")

    print("\n=== OPPORTUNITY EXCHANGE ===")

    if not opportunities:
        print("No opportunities available.")
        return

    for o in opportunities:
        print("\nID:", o["id"])
        print("Title:", o["title"])
        print("Category:", o["category"])
        print("Revenue:", o["potential_revenue_bwp"], "BWP")
        print("Status:", o["status"])


def system_status():
    print("\n======================================")
    print("BSTM ACTIVATION ENGINE")
    print("======================================")

    youth = load("youth")
    businesses = load("businesses")
    opportunities = load("opportunities")
    trials = load("trials")

    print("Youth:", len(youth))
    print("Businesses:", len(businesses))
    print("Opportunities:", len(opportunities))
    print("Trials:", len(trials))

    total_revenue = sum(
        float(y.get("revenue", 0) or 0)
        for y in youth
    )

    print("Tracked Youth Revenue:", total_revenue, "BWP")


def menu():
    ensure_data()

    while True:
        print("""
=========================================
BSTM ECOSYSTEM ACTIVATION ENGINE
=========================================

1. Register Youth
2. Register Business
3. Create Trial
4. Create Opportunity
5. View Youth
6. View Businesses
7. View Opportunity Exchange
8. System Status
9. Exit

=========================================
""")

        choice = input("BSTM > ").strip()

        if choice == "1":
            register_youth()

        elif choice == "2":
            register_business()

        elif choice == "3":
            create_trial()

        elif choice == "4":
            create_opportunity()

        elif choice == "5":
            view_youth()

        elif choice == "6":
            view_businesses()

        elif choice == "7":
            view_opportunities()

        elif choice == "8":
            system_status()

        elif choice == "9":
            print("BSTM Activation Engine shutting down.")
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    menu()
