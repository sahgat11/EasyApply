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

    removable_words = {
        "summer",
        "usa",
        "us",
        "2027",
    }

    words = [
        word
        for word in role.split()
        if word not in removable_words
    ]

    return " ".join(words)


def is_wrong_recruiting_cycle(role):
    if not role:
        return False

    text = normalize_text(role)

    wrong_cycle_terms = [
        "fall 2026",
        "winter 2026",
        "summer 2026",
        "spring 2026",
    ]

    return any(
        term in text
        for term in wrong_cycle_terms
    )


def roles_match(role1, role2):
    # Both unknown means they can belong together
    if not role1 and not role2:
        return True

    # One known and one unknown needs special handling elsewhere
    if not role1 or not role2:
        return False

    role1 = normalize_role(role1)
    role2 = normalize_role(role2)

    if role1 == role2:
        return True

    if role1 in role2 or role2 in role1:
        shorter = min(
            len(role1.split()),
            len(role2.split())
        )

        longer = max(
            len(role1.split()),
            len(role2.split())
        )

        if longer and shorter / longer >= 0.75:
            return True

    words1 = set(role1.split())
    words2 = set(role2.split())

    if not words1 or not words2:
        return False

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    similarity = intersection / union

    return similarity >= 0.85


def find_existing_application(
    applications,
    company,
    role
):
    normalized_company = normalize_text(company)

    same_company = [
        application
        for application in applications
        if normalize_text(application["company"])
        == normalized_company
    ]

    # First try normal role matching
    for application in same_company:
        if roles_match(
            application["role"],
            role
        ):
            return application

    # Incoming email has no role.
    # If there is only one application for this company,
    # it is reasonable to attach the email to it.
    if not role:
        if len(same_company) == 1:
            return same_company[0]

        unknown_applications = [
            application
            for application in same_company
            if not application["role"]
        ]

        if len(unknown_applications) == 1:
            return unknown_applications[0]

        return None

    # Incoming email DOES have a role.
    # If the only application for this company currently has
    # an unknown role, promote that application to this known role.
    if role and len(same_company) == 1:
        if not same_company[0]["role"]:
            return same_company[0]

    return None


def build_applications(results):
    applications = []

    # Gmail results are newest first.
    # Process oldest -> newest.
    for result in reversed(results):
        classification = result["classification"]
        email = result["email"]

        if not classification.get(
            "is_application_update"
        ):
            continue

        company = classification.get("company")
        role = classification.get("role")

        if not company:
            continue

        # Remove old recruiting cycles.
        if is_wrong_recruiting_cycle(role):
            continue

        stage = classification.get(
            "stage",
            "UNKNOWN"
        )

        status = classification.get(
            "status",
            "UNKNOWN"
        )

        next_action = classification.get(
            "next_action"
        )

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

        # Upgrade an unknown role once we learn the actual title.
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

        # Only advance, never regress because of a generic email.
        if new_priority >= current_priority:
            application["stage"] = stage
            application["status"] = status

        # Newer explicit action replaces older action.
        if next_action:
            application["next_action"] = next_action

        application["last_update"] = email["date"]

    return applications