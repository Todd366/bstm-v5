import json

from app.api.service import (
    activate_business,
    activate_youth,
    create_business_opportunity,
    get_business_opportunity,
    get_dashboard,
    list_business_opportunities,
    list_businesses,
    list_youth
)


def ask_required(label):

    while True:

        value = input(
            label
        ).strip()

        if value:

            return value

        print(
            "Required."
        )


def ask_optional(label):

    value = input(
        label
    ).strip()

    return value or None


def activate_youth_cli():

    print(
        "\n=== YOUTH ACTIVATION ==="
    )

    data = {

        "name":
            ask_required(
                "Name: "
            ),

        "location":
            ask_required(
                "Location: "
            ),

        "passion":
            ask_required(
                "Passion / interests: "
            ),

        "goal":
            ask_required(
                "Main goal: "
            ),

        "skills":
            ask_optional(
                "Skills: "
            ),

        "availability":
            ask_optional(
                "Availability: "
            ),

        "equipment":
            ask_optional(
                "Equipment / resources: "
            )
    }

    try:

        result = activate_youth(
            data
        )

        print(
            "\nYOUTH ACTIVATED"
        )

        print(
            "ID:",
            result["id"]
        )

    except ValueError as error:

        print(
            "\nERROR:",
            error
        )


def activate_business_cli():

    print(
        "\n=== BUSINESS ACTIVATION ==="
    )

    data = {

        "name":
            ask_required(
                "Business name: "
            ),

        "owner":
            ask_required(
                "Owner / contact: "
            ),

        "sector":
            ask_required(
                "Sector: "
            ),

        "location":
            ask_required(
                "Location: "
            ),

        "main_problem":
            ask_required(
                "Main problem: "
            )
    }

    try:

        result = activate_business(
            data
        )

        print(
            "\nBUSINESS ACTIVATED"
        )

        print(
            "ID:",
            result["id"]
        )

    except ValueError as error:

        print(
            "\nERROR:",
            error
        )


def create_opportunity_cli():

    print(
        "\n=== CREATE OPPORTUNITY ==="
    )

    data = {

        "business_id":
            ask_required(
                "Business ID: "
            ),

        "title":
            ask_required(
                "Opportunity title: "
            ),

        "description":
            ask_optional(
                "Description: "
            )
    }

    try:

        result = create_business_opportunity(
            data
        )

        print(
            "\nOPPORTUNITY CREATED"
        )

        print(
            "ID:",
            result["id"]
        )

    except ValueError as error:

        print(
            "\nERROR:",
            error
        )


def show_youth():

    records = list_youth()

    print(
        "\n=== YOUTH ==="
    )

    if not records:

        print(
            "No youth records."
        )

        return

    for person in records:

        print(
            f"{person['id']} | "
            f"{person['name']} | "
            f"{person['location']} | "
            f"{person['level']}"
        )


def show_businesses():

    records = list_businesses()

    print(
        "\n=== BUSINESSES ==="
    )

    if not records:

        print(
            "No business records."
        )

        return

    for business in records:

        print(
            f"{business['id']} | "
            f"{business['name']} | "
            f"{business['sector']} | "
            f"{business['location']} | "
            f"Opportunities: "
            f"{business['opportunities_generated']}"
        )


def show_opportunities():

    records = list_business_opportunities()

    print(
        "\n=== OPPORTUNITIES ==="
    )

    if not records:

        print(
            "No opportunities."
        )

        return

    for opportunity in records:

        print(
            f"{opportunity['id']} | "
            f"{opportunity['business_name']} | "
            f"{opportunity['title']} | "
            f"{opportunity['status']}"
        )


def show_opportunity_details():

    opportunity_id = ask_required(
        "Opportunity ID: "
    )

    try:

        opportunity = get_business_opportunity(
            opportunity_id
        )

        print(
            "\n=== OPPORTUNITY ==="
        )

        print(
            json.dumps(
                opportunity,
                indent=2
            )
        )

    except ValueError as error:

        print(
            "\nERROR:",
            error
        )


def show_dashboard():

    dashboard = get_dashboard()

    print(
        "\n=== BSTM DASHBOARD ==="
    )

    print(
        json.dumps(
            dashboard,
            indent=2
        )
    )


def run():

    while True:

        print(
            """
==========================================
 BSTM PLATFORM V5
==========================================

1. Activate Youth
2. Activate Business
3. List Youth
4. List Businesses
5. Create Opportunity
6. List Opportunities
7. Opportunity Details
8. Dashboard
9. Exit

==========================================
"""
        )

        choice = input(
            "BSTM > "
        ).strip()

        if choice == "1":

            activate_youth_cli()

        elif choice == "2":

            activate_business_cli()

        elif choice == "3":

            show_youth()

        elif choice == "4":

            show_businesses()

        elif choice == "5":

            create_opportunity_cli()

        elif choice == "6":

            show_opportunities()

        elif choice == "7":

            show_opportunity_details()

        elif choice == "8":

            show_dashboard()

        elif choice == "9":

            print(
                "BSTM shutting down."
            )

            break

        else:

            print(
                "Invalid option."
            )


if __name__ == "__main__":

    run()
