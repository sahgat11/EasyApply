from easyapply.gmail_client import get_gmail_service
from easyapply.email_scanner import find_application_emails
from easyapply.email_reader import get_email_body
from easyapply.classifier import classify_email


def main():
    service = get_gmail_service()

    profile = service.users().getProfile(userId="me").execute()
    user_email = profile["emailAddress"]

    print("Connected to Gmail!")
    print("Email:", user_email)
    print()

    emails = find_application_emails(
        service,
        user_email=user_email,
        max_results=200
    )

    print(f"Found {len(emails)} candidate emails.")
    print("Testing AI classification on the 5 most recent...\n")

    for email in emails[:5]:
        print("=" * 70)
        print("Subject:", email["subject"])

        body = get_email_body(service, email["id"])

        classification = classify_email(email, body)

        if classification:
            print("Company:", classification.get("company"))
            print("Role:", classification.get("role"))
            print("Stage:", classification.get("stage"))
            print("Status:", classification.get("status"))
            print("Next action:", classification.get("next_action"))
            print(
                "Application update:",
                classification.get("is_application_update")
            )

        print()


if __name__ == "__main__":
    main()