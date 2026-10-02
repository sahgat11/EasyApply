import re


STAGE_PRIORITY = {
    "UNKNOWN": 0,
    "APPLIED": 1,
    "ONLINE_ASSESSMENT": 2,
    "RECRUITER_SCREEN": 3,
    "TECHNICAL_INTERVIEW": 4,
    "FINAL_INTERVIEW": 5,
    "OFFER": 6,
    "REJECTED": 7,
    "WITHDRAWN": 7,
}


def normalize_text(value):
    if not value:
        return ""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def normalize_role(role):
    if not role:
        return ""

    role = normalize_text(role)

    removable_words = [
        "summer",
        "usa",
        "us",
        "2027",
    ]

    words = role.split()

    words = [
        word
        for word in words
        if word not in removable_words
    ]

    return " ".join(words)


def roles_match(role1, role2):
    if not role1 or not role2:
        return True

    role1 = normalize_role(role1)
    role2 = normalize_role(role2)

    if role1 == role2:
        return True

    words1 = set(role1.split())
    words2 = set(role2.split())

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2)
    smaller = min(len(words1), len(words2))

    return overlap / smaller >= 0.75


def find_existing_application(applications, company, role):
    normalized_company = normalize_text(company)

    for application in applications:
        if normalize_text(application["company"]) != normalized_company:
            continue

        if roles_match(application["role"], role):
            return application

    return None


def build_applications(results):
    applications = []

    # Emails arrive newest first.
    # Reverse so we process application history chronologically.
    for result in reversed(results):
        classification = result["classification"]
        email = result["email"]

        if not classification.get("is_application_update"):
            continue

        company = classification.get("company")

        if not company:
            continue

        role = classification.get("role")
        stage = classification.get("stage", "UNKNOWN")
        status = classification.get("status", "UNKNOWN")
        next_action = classification.get("next_action")

        application = find_existing_application(
            applications,
            company,
            role
        )

        if application is None:
            application = {
                "company": company,
                "role": role,
                "stage": stage,
                "status": status,
                "next_action": next_action,
                "last_update": email["date"],
                "email_count": 1,
            }

            applications.append(application)
            continue

        application["email_count"] += 1

        # Prefer a known role over a missing role
        if not application["role"] and role:
            application["role"] = role

        current_priority = STAGE_PRIORITY.get(
            application["stage"],
            0
        )

        new_priority = STAGE_PRIORITY.get(
            stage,
            0
        )

        # Advance application when the new email represents
        # a later recruiting stage.
        if new_priority >= current_priority:
            application["stage"] = stage
            application["status"] = status

        if next_action:
            application["next_action"] = next_action

        application["last_update"] = email["date"]

    return applications