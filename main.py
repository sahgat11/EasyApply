from easyapply.gmail_client import get_gmail_service
from easyapply.email_scanner import find_application_emails


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

    print(
        f"Found {len(emails)} likely internship application emails "
        f"from the last 3 months.\n"
    )

    for email in emails:
        print("=" * 70)
        print("From:", email["from"])
        print("Subject:", email["subject"])
        print("Date:", email["date"])

    if not emails:
        print("No application emails found.")


if __name__ == "__main__":
    main()