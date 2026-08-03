from app.core.config import (
    APP_NAME,
    APP_VERSION
)

from app.core.health import (
    system_health
)

from app.db.database import (
    initialize_database
)


def main():

    initialize_database()

    health = system_health()

    print(
        "=========================================="
    )

    print(
        f"{APP_NAME} V{APP_VERSION}"
    )

    print(
        "FOUNDATION CORE ONLINE"
    )

    print(
        "=========================================="
    )

    print(
        f"Database: {health['database']}"
    )

    print(
        f"Youth: {health['counts']['youth']}"
    )

    print(
        f"Businesses: {health['counts']['businesses']}"
    )

    print(
        f"Opportunities: {health['counts']['opportunities']}"
    )

    print(
        f"Trials: {health['counts']['trials']}"
    )


if __name__ == "__main__":

    main()
