from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID_FILE = Path("data/sheet_id.txt")

SPREADSHEET_TITLE = "EasyApply - Summer 2027 Internship Tracker"


def get_sheets_service():
    credentials = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials
    )


def get_or_create_spreadsheet(service):
    SHEET_ID_FILE.parent.mkdir(exist_ok=True)

    # Reuse the existing spreadsheet
    if SHEET_ID_FILE.exists():
        spreadsheet_id = SHEET_ID_FILE.read_text().strip()

        if spreadsheet_id:
            return spreadsheet_id

    # Create spreadsheet the first time
    spreadsheet = (
        service.spreadsheets()
        .create(
            body={
                "properties": {
                    "title": SPREADSHEET_TITLE
                }
            }
        )
        .execute()
    )

    spreadsheet_id = spreadsheet["spreadsheetId"]

    SHEET_ID_FILE.write_text(spreadsheet_id)

    return spreadsheet_id


def sort_applications(applications):
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
            application["company"].lower(),
            (application["role"] or "").lower(),
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
            "Last Updated",
            "Emails",
        ]
    ]

    applications = sort_applications(applications)

    for application in applications:
        rows.append(
            [
                application["company"],
                application["role"] or "Unknown",
                application["stage"],
                application["status"],
                application["next_action"] or "",
                application["last_update"],
                application["email_count"],
            ]
        )

    return rows


def sync_applications_to_sheet(applications):
    service = get_sheets_service()

    spreadsheet_id = get_or_create_spreadsheet(
        service
    )

    rows = build_rows(applications)

    # Clear old application data
    (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:G",
            body={}
        )
        .execute()
    )

    # Write current application data
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
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
            spreadsheetId=spreadsheet_id
        )
        .execute()
    )

    sheet_id = None

    for sheet in spreadsheet["sheets"]:
        if sheet["properties"]["title"] == "Sheet1":
            sheet_id = sheet["properties"]["sheetId"]
            break

    if sheet_id is None:
        raise RuntimeError(
            "Could not find Sheet1 in spreadsheet."
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
    row_count = len(applications) + 1

    requests = [
        # Freeze header
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        },

        # Header styling
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7,
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
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat"
            }
        },

        # Body formatting
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7,
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": (
                    "userEnteredFormat.verticalAlignment,"
                    "userEnteredFormat.wrapStrategy"
                )
            }
        },

        # Company width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {
                    "pixelSize": 180
                },
                "fields": "pixelSize"
            }
        },

        # Role width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": 2,
                },
                "properties": {
                    "pixelSize": 360
                },
                "fields": "pixelSize"
            }
        },

        # Stage + Status widths
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,
                    "endIndex": 4,
                },
                "properties": {
                    "pixelSize": 165
                },
                "fields": "pixelSize"
            }
        },

        # Next Action width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 4,
                    "endIndex": 5,
                },
                "properties": {
                    "pixelSize": 320
                },
                "fields": "pixelSize"
            }
        },

        # Last Updated width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,
                    "endIndex": 6,
                },
                "properties": {
                    "pixelSize": 240
                },
                "fields": "pixelSize"
            }
        },

        # Emails width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 6,
                    "endIndex": 7,
                },
                "properties": {
                    "pixelSize": 80
                },
                "fields": "pixelSize"
            }
        },

        # Filter
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,
                        "endColumnIndex": 7,
                    }
                }
            }
        },
    ]

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

    sorted_applications = sort_applications(
        applications
    )

    for index, application in enumerate(
        sorted_applications,
        start=1
    ):
        stage = application["stage"]

        color = stage_colors.get(
            stage,
            stage_colors["UNKNOWN"]
        )

        # Color Stage cell
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": index,
                        "endRowIndex": index + 1,
                        "startColumnIndex": 2,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                            "textFormat": {
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            }
        )

        # Status coloring
        if application["status"] == "CLOSED":
            status_color = {
                "red": 0.96,
                "green": 0.75,
                "blue": 0.75,
            }

        elif application["status"] == "ACTIVE":
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
                        "sheetId": sheet_id,
                        "startRowIndex": index,
                        "endRowIndex": index + 1,
                        "startColumnIndex": 3,
                        "endColumnIndex": 4,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": status_color,
                            "textFormat": {
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            }
        )

    (
        service.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
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
            spreadsheetId=spreadsheet_id
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

    # Create Dashboard if it does not exist
    if dashboard_sheet is None:
        result = (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": "Dashboard",
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
            result["replies"][0]["addSheet"]
        )

    dashboard_id = (
        dashboard_sheet["properties"]["sheetId"]
    )

    total = len(applications)

    active = sum(
        1
        for app in applications
        if app["status"] == "ACTIVE"
    )

    applied = sum(
        1
        for app in applications
        if app["stage"] == "APPLIED"
    )

    assessments = sum(
        1
        for app in applications
        if app["stage"] == "ONLINE_ASSESSMENT"
    )

    interviews = sum(
        1
        for app in applications
        if app["stage"] in {
            "RECRUITER_SCREEN",
            "TECHNICAL_INTERVIEW",
            "FINAL_INTERVIEW",
        }
    )

    offers = sum(
        1
        for app in applications
        if app["stage"] == "OFFER"
    )

    rejected = sum(
        1
        for app in applications
        if app["stage"] == "REJECTED"
    )

    unknown = sum(
        1
        for app in applications
        if app["stage"] == "UNKNOWN"
    )

    action_needed = sum(
        1
        for app in applications
        if (
            app["next_action"]
            and app["status"] == "ACTIVE"
        )
    )

    rows = [
        ["EasyApply Dashboard", ""],
        ["Summer 2027 Internship Tracker", ""],
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
        ["Online Assessments", assessments],
        ["Interviews", interviews],
        ["Offers", offers],
        ["Rejected", rejected],
        ["Unknown", unknown],
        ["Action Needed", action_needed],
    ]

    # Clear old dashboard values
    (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId=spreadsheet_id,
            range="Dashboard!A:Z",
            body={}
        )
        .execute()
    )

    # Write dashboard
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range="Dashboard!A1",
            valueInputOption="RAW",
            body={
                "values": rows
            }
        )
        .execute()
    )

    requests = [
        # Dashboard title
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_id,
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
                "fields": "userEnteredFormat"
            }
        },

        # Metric header
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_id,
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
                "fields": "userEnteredFormat"
            }
        },

        # Metric labels
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_id,
                    "startRowIndex": 5,
                    "endRowIndex": 14,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True
                        }
                    }
                },
                "fields": "userEnteredFormat"
            }
        },

        # Count styling
        {
            "repeatCell": {
                "range": {
                    "sheetId": dashboard_id,
                    "startRowIndex": 5,
                    "endRowIndex": 14,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2,
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "bold": True,
                            "fontSize": 14
                        }
                    }
                },
                "fields": "userEnteredFormat"
            }
        },

        # Column A width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": dashboard_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                },
                "properties": {
                    "pixelSize": 230
                },
                "fields": "pixelSize"
            }
        },

        # Column B width
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": dashboard_id,
                    "dimension": "COLUMNS",
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
            spreadsheetId=spreadsheet_id,
            body={
                "requests": requests
            }
        )
        .execute()
    )