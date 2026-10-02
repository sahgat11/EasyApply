from easyapply.gmail_client import get_gmail_service


def main():
    service = get_gmail_service()

    profile = service.users().getProfile(userId="me").execute()

    print("Connected to Gmail!")
    print("Email:", profile["emailAddress"])


if __name__ == "__main__":
    main()