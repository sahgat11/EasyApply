BLOCKED_SENDERS = [
    "lensa.com",
    "swelist.com",
    "piazza.com",
]

BLOCKED_SUBJECT_PHRASES = [
    "new internships posted",
    "jobs in san francisco",
    "new roles at",
    "job alert",
    "jobs posted",
    "confirmation of enrollment",
    "fellowship applications reminder",
    "how would you rate the support",
]

APPLICATION_KEYWORDS = [
    "thank you for applying",
    "thanks for applying",
    "application",
    "assessment",
    "interview",
    "candidate",
    "recruiting",
    "talent acquisition",
    "online assessment",
    "coding assessment",
    "technical interview",
    "phone interview",
    "recruiter",
    "offer",
    "unfortunately",
    "move forward",
    "next steps",
    "action required",
]


def is_likely_application_email(email, user_email):
    sender = email["from"].lower()
    subject = email["subject"].lower()

    # Ignore emails sent by yourself
    if user_email.lower() in sender:
        return False

    # Ignore known job-alert/newsletter sites
    for blocked_sender in BLOCKED_SENDERS:
        if blocked_sender in sender:
            return False

    # Ignore obvious newsletters / irrelevant messages
    for phrase in BLOCKED_SUBJECT_PHRASES:
        if phrase in subject:
            return False

    # Keep emails that appear related to an actual application process
    for keyword in APPLICATION_KEYWORDS:
        if keyword in subject or keyword in sender:
            return True

    return False


def find_application_emails(service, user_email, max_results=200):
    query = (
        'newer_than:3m '
        '(intern OR internship OR application OR interview '
        'OR assessment OR recruiter OR candidate OR hiring)'
    )

    messages = []
    page_token = None

    while len(messages) < max_results:
        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(100, max_results - len(messages)),
                pageToken=page_token
            )
            .execute()
        )

        messages.extend(result.get("messages", []))

        page_token = result.get("nextPageToken")

        if not page_token:
            break

    emails = []

    for message in messages:
        data = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            )
            .execute()
        )

        headers = data["payload"].get("headers", [])

        email_info = {
            "id": message["id"],
            "from": "",
            "subject": "",
            "date": ""
        }

        for header in headers:
            name = header.get("name", "")
            value = header.get("value", "")

            if name == "From":
                email_info["from"] = value

            elif name == "Subject":
                email_info["subject"] = value

            elif name == "Date":
                email_info["date"] = value

        if is_likely_application_email(email_info, user_email):
            emails.append(email_info)

    return emails