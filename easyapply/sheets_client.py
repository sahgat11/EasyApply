from datetime import datetime, date
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID_FILE = Path(
    "data/sheet_id.txt"
)

SPREADSHEET_TITLE = (
    "EasyApply - Summer 2027 Internship Tracker"
)


def get_sheets_service():
    credentials = (
        Credentials
        .from_authorized_user_file(
            "token.json",
            SCOPES
        )
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials
    )


def get_or_create_spreadsheet(
    service
):
    SHEET_ID_FILE.parent.mkdir(
        exist_ok=True
    )

    if SHEET_ID_FILE.exists():
        spreadsheet_id = (
            SHEET_ID_FILE
            .read_text()
            .strip()
        )

        if spreadsheet_id:
            return spreadsheet_id

    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {
                    "title": (
                        SPREADSHEET_TITLE
                    )
                }
            }
        )
        .execute()
    )

    spreadsheet_id = (
        spreadsheet["spreadsheetId"]
    )

    SHEET_ID_FILE.write_text(
        spreadsheet_id
    )

    return spreadsheet_id


def sort_applications(
    applications
):
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

    return sorted(
        applications,
        key=lambda application: (
            stage_order.get(
                application["stage"],
                99
            ),
            application[
                "company"
            ].lower(),
            (
                application["role"]
                or ""
            ).lower(),
        )
    )


def build_rows(applications):
    rows = [
        [
            "Company",
            "Role",
            "Stage",
            "Status",
            "Next Action",
            "Deadline",
            "Last Updated",
            "Emails",
        ]
    ]

    applications = (
        sort_applications(
            applications
        )
    )

    for application in applications:
        rows.append(
            [
                application["company"],
                (
                    application["role"]
                    or "Unknown"
                ),
                application["stage"],
                application["status"],
                (
                    application[
                        "next_action"
                    ]
                    or ""
                ),
                (
                    application.get(
                        "deadline"
                    )
                    or ""
                ),
                application[
                    "last_update"
                ],
                application[
                    "email_count"
                ],
            ]
        )

    return rows


def sync_applications_to_sheet(
    applications
):
    service = get_sheets_service()

    spreadsheet_id = (
        get_or_create_spreadsheet(
            service
        )
    )

    rows = build_rows(
        applications
    )

    (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId=(
                spreadsheet_id
            ),
            range="Sheet1!A:H",
            body={}
        )
        .execute()
    )

    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=(
                spreadsheet_id
            ),
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={
                "values": rows
            }
        )
        .execute()
    )

    spreadsheet = (
        service.spreadsheets()
        .get(
            spreadsheetId=(
                spreadsheet_id
            )
        )
        .execute()
    )

    sheet_id = None

    for sheet in spreadsheet["sheets"]:
        if (
            sheet["properties"]["title"]
            == "Sheet1"
        ):
            sheet_id = (
                sheet["properties"][
                    "sheetId"
                ]
            )

            break

    if sheet_id is None:
        raise RuntimeError(
            "Could not find Sheet1."
        )

    format_sheet(
        service,
        spreadsheet_id,
        sheet_id,
        applications
    )

    update_dashboard(
        service,
        spreadsheet_id,
        applications
    )

    return spreadsheet_id


def format_sheet(
    service,
    spreadsheet_id,
    sheet_id,
    applications
):
    row_count = (
        len(applications) + 1
    )

    requests = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": (
                    "gridProperties."
                    "frozenRowCount"
                )
            }
        },

        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 8,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.12,
                            "green": 0.20,
                            "blue": 0.32,
                        },
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            }
                        },
                        "horizontalAlignment": (
                            "CENTER"
                        ),
                        "verticalAlignment": (
                            "MIDDLE"
                        ),
                    }
                },
                "fields": (
                    "userEnteredFormat"
                )
            }
        },

        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": 8,
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": (
                            "MIDDLE"
                        ),
                        "wrapStrategy": (
                            "WRAP"
                        ),
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "verticalAlignment,"
                    "userEnteredFormat."
                    "wrapStrategy"
                )
            }
        },

        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": (
                            row_count
                        ),
                        "startColumnIndex": 0,
                        "endColumnIndex": 8,
                    }
                }
            }
        },
    ]

    widths = [
        (0, 1, 180),
        (1, 2, 360),
        (2, 4, 165),
        (4, 5, 300),
        (5, 6, 120),
        (6, 7, 240),
        (7, 8, 80),
    ]

    for start, end, size in widths:
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": (
                            sheet_id
                        ),
                        "dimension": (
                            "COLUMNS"
                        ),
                        "startIndex": start,
                        "endIndex": end,
                    },
                    "properties": {
                        "pixelSize": size
                    },
                    "fields": (
                        "pixelSize"
                    )
                }
            }
        )

    stage_colors = {
        "APPLIED": {
            "red": 0.85,
            "green": 0.92,
            "blue": 1.0,
        },
        "ONLINE_ASSESSMENT": {
            "red": 1.0,
            "green": 0.93,
            "blue": 0.70,
        },
        "RECRUITER_SCREEN": {
            "red": 0.83,
            "green": 0.95,
            "blue": 0.83,
        },
        "TECHNICAL_INTERVIEW": {
            "red": 0.75,
            "green": 0.92,
            "blue": 0.77,
        },
        "FINAL_INTERVIEW": {
            "red": 0.66,
            "green": 0.90,
            "blue": 0.72,
        },
        "OFFER": {
            "red": 0.57,
            "green": 0.88,
            "blue": 0.65,
        },
        "REJECTED": {
            "red": 0.96,
            "green": 0.75,
            "blue": 0.75,
        },
        "WITHDRAWN": {
            "red": 0.90,
            "green": 0.90,
            "blue": 0.90,
        },
        "UNKNOWN": {
            "red": 0.90,
            "green": 0.90,
            "blue": 0.90,
        },
    }

    sorted_apps = sort_applications(
        applications
    )

    today = date.today()

    for index, application in enumerate(
        sorted_apps,
        start=1
    ):
        stage_color = (
            stage_colors.get(
                application["stage"],
                stage_colors["UNKNOWN"]
            )
        )

        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": (
                            sheet_id
                        ),
                        "startRowIndex": (
                            index
                        ),
                        "endRowIndex": (
                            index + 1
                        ),
                        "startColumnIndex": 2,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": (
                                stage_color
                            ),
                            "textFormat": {
                                "bold": True
                            },
                            "horizontalAlignment": (
                                "CENTER"
                            ),
                        }
                    },
                    "fields": (
                        "userEnteredFormat"
                    )
                }
            }
        )

        status = application[
            "status"
        ]

        if status == "CLOSED":
            status_color = {
                "red": 0.96,
                "green": 0.75,
                "blue": 0.75,
            }

        elif status == "ACTIVE":
            status_color = {
                "red": 0.80,
                "green": 0.93,
                "blue": 0.80,
            }

        else:
            status_color = {
                "red": 0.90,
                "green": 0.90,
                "blue": 0.90,
            }

        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": (
                            sheet_id
                        ),
                        "startRowIndex": index,
                        "endRowIndex": (
                            index + 1
                        ),
                        "startColumnIndex": 3,
                        "endColumnIndex": 4,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": (
                                status_color
                            ),
                            "textFormat": {
                                "bold": True
                            },
                            "horizontalAlignment": (
                                "CENTER"
                            ),
                        }
                    },
                    "fields": (
                        "userEnteredFormat"
                    )
                }
            }
        )

        deadline = application.get(
            "deadline"
        )

        if deadline:
            try:
                deadline_date = (
                    datetime.strptime(
                        deadline,
                        "%Y-%m-%d"
                    ).date()
                )

                days_left = (
                    deadline_date - today
                ).days

                if days_left < 0:
                    deadline_color = {
                        "red": 0.96,
                        "green": 0.65,
                        "blue": 0.65,
                    }

                elif days_left <= 3:
                    deadline_color = {
                        "red": 1.0,
                        "green": 0.90,
                        "blue": 0.55,
                    }

                else:
                    deadline_color = {
                        "red": 0.80,
                        "green": 0.93,
                        "blue": 0.80,
                    }

                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": (
                                    sheet_id
                                ),
                                "startRowIndex": (
                                    index
                                ),
                                "endRowIndex": (
                                    index + 1
                                ),
                                "startColumnIndex": 5,
                                "endColumnIndex": 6,
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": (
                                        deadline_color
                                    ),
                                    "textFormat": {
                                        "bold": True
                                    },
                                    "horizontalAlignment": (
                                        "CENTER"
                                    ),
                                }
                            },
                            "fields": (
                                "userEnteredFormat"
                            )
                        }
                    }
                )

            except ValueError:
                pass

    (
        service.spreadsheets()
        .batchUpdate(
            spreadsheetId=(
                spreadsheet_id
            ),
            body={
                "requests": requests
            }
        )
        .execute()
    )


def update_dashboard(
    service,
    spreadsheet_id,
    applications
):
    spreadsheet = (
        service.spreadsheets()
        .get(
            spreadsheetId=(
                spreadsheet_id
            )
        )
        .execute()
    )

    dashboard_sheet = None

    for sheet in spreadsheet["sheets"]:
        if (
            sheet["properties"]["title"]
            == "Dashboard"
        ):
            dashboard_sheet = sheet
            break

    if dashboard_sheet is None:
        result = (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=(
                    spreadsheet_id
                ),
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": (
                                        "Dashboard"
                                    ),
                                    "index": 0
                                }
                            }
                        }
                    ]
                }
            )
            .execute()
        )

        dashboard_sheet = (
            result["replies"][0][
                "addSheet"
            ]
        )

    dashboard_id = (
        dashboard_sheet[
            "properties"
        ]["sheetId"]
    )

    total = len(applications)

    active = sum(
        app["status"] == "ACTIVE"
        for app in applications
    )

    applied = sum(
        app["stage"] == "APPLIED"
        for app in applications
    )

    assessments = sum(
        app["stage"]
        == "ONLINE_ASSESSMENT"
        for app in applications
    )

    interviews = sum(
        app["stage"] in {
            "RECRUITER_SCREEN",
            "TECHNICAL_INTERVIEW",
            "FINAL_INTERVIEW",
        }
        for app in applications
    )

    offers = sum(
        app["stage"] == "OFFER"
        for app in applications
    )

    rejected = sum(
        app["stage"] == "REJECTED"
        for app in applications
    )

    action_needed = sum(
        bool(app["next_action"])
        and app["status"] == "ACTIVE"
        for app in applications
    )

    deadlines = sum(
        bool(app.get("deadline"))
        and app["status"] == "ACTIVE"
        for app in applications
    )

    rows = [
        [
            "EasyApply Dashboard",
            ""
        ],
        [
            "Summer 2027 Internship Tracker",
            ""
        ],
        [
            "Last Sync",
            datetime.now().strftime(
                "%b %d, %Y %I:%M %p"
            )
        ],
        ["", ""],
        ["Metric", "Count"],
        ["Total Applications", total],
        ["Active", active],
        ["Applied", applied],
        [
            "Online Assessments",
            assessments
        ],
        ["Interviews", interviews],
        ["Offers", offers],
        ["Rejected", rejected],
        [
            "Action Needed",
            action_needed
        ],
        [
            "Active Deadlines",
            deadlines
        ],
    ]

    (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId=(
                spreadsheet_id
            ),
            range="Dashboard!A:Z",
            body={}
        )
        .execute()
    )

    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=(
                spreadsheet_id
            ),
            range="Dashboard!A1",
            valueInputOption="RAW",
            body={
                "values": rows
            }
        )
        .execute()
    )

    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": (
                        dashboard_id
                    ),
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.12,
                            "green": 0.20,
                            "blue": 0.32,
                        },
                        "textFormat": {
                            "bold": True,
                            "fontSize": 18,
                            "foregroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            },
                        }
                    }
                },
                "fields": (
                    "userEnteredFormat"
                )
            }
        },

        {
            "repeatCell": {
                "range": {
                    "sheetId": (
                        dashboard_id
                    ),
                    "startRowIndex": 4,
                    "endRowIndex": 5,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.75,
                            "green": 0.82,
                            "blue": 0.92,
                        },
                        "textFormat": {
                            "bold": True
                        }
                    }
                },
                "fields": (
                    "userEnteredFormat"
                )
            }
        },

        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": (
                        dashboard_id
                    ),
                    "dimension": (
                        "COLUMNS"
                    ),
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {
                    "pixelSize": 230
                },
                "fields": "pixelSize"
            }
        },

        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": (
                        dashboard_id
                    ),
                    "dimension": (
                        "COLUMNS"
                    ),
                    "startIndex": 1,
                    "endIndex": 2,
                },
                "properties": {
                    "pixelSize": 170
                },
                "fields": "pixelSize"
            }
        },
    ]

    (
        service.spreadsheets()
        .batchUpdate(
            spreadsheetId=(
                spreadsheet_id
            ),
            body={
                "requests": requests
            }
        )
        .execute()
    )