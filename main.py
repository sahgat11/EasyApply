import argparse

from easyapply.gmail_client import (
    get_gmail_service
)
from easyapply.email_scanner import (
    find_application_emails
)
from easyapply.email_reader import (
    get_email_body
)
from easyapply.classifier import (
    classify_email
)
from easyapply.database import (
    initialize_database,
    get_classification,
    save_classification,
)
from easyapply.application_tracker import (
    build_applications
)
from easyapply.sheets_client import (
    sync_applications_to_sheet
)


def load_applications(
    verbose=False,
    force_refresh=False
):
    initialize_database()

    service = get_gmail_service()

    profile = (
        service.users()
        .getProfile(
            userId="me"
        )
        .execute(
            num_retries=5
        )
    )

    user_email = (
        profile["emailAddress"]
    )

    emails = find_application_emails(
        service,
        user_email=user_email,
        max_results=200
    )

    results = []

    new_classifications = 0
    cached_classifications = 0
    ignored_emails = 0

    for index, email in enumerate(
        emails,
        start=1
    ):
        classification = None

        if not force_refresh:
            classification = (
                get_classification(
                    email["id"]
                )
            )

        if classification is None:
            if verbose:
                print(
                    f"[{index}/{len(emails)}] "
                    f"Processing: "
                    f"{email['subject'][:55]}"
                )

            body = get_email_body(
                service,
                email["id"]
            )

            classification = (
                classify_email(
                    email,
                    body
                )
            )

            if classification:
                save_classification(
                    email,
                    classification
                )

                new_classifications += 1

        else:
            cached_classifications += 1

        if not classification:
            continue

        if not classification.get(
            "is_application_update"
        ):
            ignored_emails += 1

        results.append(
            {
                "email": email,
                "classification": (
                    classification
                )
            }
        )

    applications = (
        build_applications(
            results
        )
    )

    stats = {
        "emails_scanned": (
            len(emails)
        ),
        "new_classifications": (
            new_classifications
        ),
        "cached_classifications": (
            cached_classifications
        ),
        "ignored_emails": (
            ignored_emails
        ),
        "applications": (
            len(applications)
        ),
    }

    return applications, stats


def sync():
    print()
    print("EasyApply Sync")
    print("=" * 40)

    applications, stats = (
        load_applications(
            verbose=True
        )
    )

    spreadsheet_id = (
        sync_applications_to_sheet(
            applications
        )
    )

    print()
    print("Sync complete")
    print("-" * 40)

    print(
        f"Emails scanned:       "
        f"{stats['emails_scanned']}"
    )

    print(
        f"New emails processed: "
        f"{stats['new_classifications']}"
    )

    print(
        f"Cached emails:        "
        f"{stats['cached_classifications']}"
    )

    print(
        f"Applications tracked: "
        f"{stats['applications']}"
    )

    print()
    print("Google Sheet:")

    print(
        "https://docs.google.com/"
        "spreadsheets/d/"
        + spreadsheet_id
    )


def refresh():
    print()
    print(
        "EasyApply Deadline Refresh"
    )
    print("=" * 40)

    print(
        "Reprocessing existing emails "
        "to extract deadlines..."
    )
    print()

    applications, stats = (
        load_applications(
            verbose=True,
            force_refresh=True
        )
    )

    spreadsheet_id = (
        sync_applications_to_sheet(
            applications
        )
    )

    deadlines = sum(
        1
        for application
        in applications
        if application.get(
            "deadline"
        )
    )

    print()
    print("Refresh complete")
    print("-" * 40)

    print(
        f"Emails reprocessed:   "
        f"{stats['new_classifications']}"
    )

    print(
        f"Applications tracked: "
        f"{stats['applications']}"
    )

    print(
        f"Deadlines found:      "
        f"{deadlines}"
    )

    print()
    print("Google Sheet:")

    print(
        "https://docs.google.com/"
        "spreadsheets/d/"
        + spreadsheet_id
    )


def list_applications():
    print()
    print(
        "EasyApply Applications"
    )
    print("=" * 70)

    applications, stats = (
        load_applications(
            verbose=False
        )
    )

    stage_order = {
        "OFFER": 0,
        "FINAL_INTERVIEW": 1,
        "TECHNICAL_INTERVIEW": 2,
        "RECRUITER_SCREEN": 3,
        "ONLINE_ASSESSMENT": 4,
        "APPLIED": 5,
        "UNKNOWN": 6,
        "REJECTED": 7,
        "WITHDRAWN": 8,
    }

    applications = sorted(
        applications,
        key=lambda app: (
            stage_order.get(
                app["stage"],
                99
            ),
            app[
                "company"
            ].lower()
        )
    )

    for application in applications:
        company = (
            application["company"]
        )

        role = (
            application["role"]
            or "Unknown"
        )

        stage = (
            application["stage"]
        )

        next_action = (
            application["next_action"]
            or "-"
        )

        deadline = (
            application.get(
                "deadline"
            )
            or "-"
        )

        print()
        print(company)

        print(
            f"  Role:        "
            f"{role}"
        )

        print(
            f"  Stage:       "
            f"{stage}"
        )

        print(
            f"  Next Action: "
            f"{next_action}"
        )

        print(
            f"  Deadline:    "
            f"{deadline}"
        )

    print()

    print(
        f"{stats['applications']} "
        f"total applications"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "AI-powered internship "
            "application tracker"
        )
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="sync",
        choices=[
            "sync",
            "list",
            "refresh",
        ],
        help="Command to run"
    )

    args = parser.parse_args()

    if args.command == "sync":
        sync()

    elif args.command == "list":
        list_applications()

    elif args.command == "refresh":
        refresh()


if __name__ == "__main__":
    main()