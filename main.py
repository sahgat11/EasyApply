from easyapply.gmail_client import get_gmail_service
from easyapply.email_scanner import find_application_emails
from easyapply.email_reader import get_email_body
from easyapply.classifier import classify_email
from easyapply.database import (
    initialize_database,
    get_classification,
    save_classification,
)
from easyapply.application_tracker import build_applications


def main():
    initialize_database()

    service = get_gmail_service()

    profile = service.users().getProfile(
        userId="me"
    ).execute()

    user_email = profile["emailAddress"]

    print("Connected to Gmail!")
    print("Email:", user_email)
    print()

    emails = find_application_emails(
        service,
        user_email=user_email,
        max_results=200
    )

    print(f"Found {len(emails)} candidate emails.\n")

    results = []

    for index, email in enumerate(emails, start=1):
        print(
            f"[{index}/{len(emails)}] "
            f"{email['subject'][:65]}"
        )

        classification = get_classification(
            email["id"]
        )

        if classification is None:
            body = get_email_body(
                service,
                email["id"]
            )

            classification = classify_email(
                email,
                body
            )

            if classification:
                save_classification(
                    email,
                    classification
                )

                print("  Classified with Groq")

        else:
            print("  Using cached classification")

        if classification:
            results.append(
                {
                    "email": email,
                    "classification": classification
                }
            )

    applications = build_applications(results)

    print()
    print("=" * 75)
    print("INTERNSHIP APPLICATIONS")
    print("=" * 75)

    for application in applications:
        print()
        print("Company:", application["company"])
        print(
            "Role:",
            application["role"] or "Unknown"
        )
        print("Stage:", application["stage"])
        print("Status:", application["status"])
        print(
            "Next Action:",
            application["next_action"] or "None"
        )
        print(
            "Emails:",
            application["email_count"]
        )

    print()
    print(
        f"Total unique applications: "
        f"{len(applications)}"
    )


if __name__ == "__main__":
    main()