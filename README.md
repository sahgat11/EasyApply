# EasyApply

EasyApply is an AI-powered internship application tracker that automatically turns recruiting emails into a structured application dashboard.

It connects to Gmail, detects internship-related emails, uses an LLM to extract recruiting information, groups related emails into individual applications, stores classifications locally, and synchronizes the latest application state to Google Sheets.

## Features

- Scans recent Gmail messages for internship recruiting emails
- Extracts structured application data using an LLM
- Identifies:
  - Company
  - Job title
  - Application stage
  - Application status
  - Required next action
- Groups multiple recruiting emails into the same application
- Distinguishes multiple roles at the same company
- Tracks stages including:
  - Applied
  - Online Assessment
  - Recruiter Screen
  - Technical Interview
  - Final Interview
  - Offer
  - Rejected
  - Withdrawn
- Stores classifications in SQLite to avoid redundant LLM calls
- Processes only newly discovered emails during normal syncs
- Automatically updates a formatted Google Sheets tracker
- Generates a dashboard summarizing application activity
- Retries temporary Gmail and LLM API failures
- Filters newsletters, job alerts, and unrelated recruiting content

## How It Works

```text
Gmail
  |
  v
Email Scanner
  |
  v
Email Body Extraction
  |
  v
LLM Classification
  |
  v
SQLite Cache
  |
  v
Application Matching / Deduplication
  |
  v
Google Sheets Tracker + Dashboard
```

EasyApply first searches Gmail for messages likely related to internship applications.

Each new email is passed through an LLM that returns structured JSON containing information such as the employer, role, recruiting stage, status, and next action.

The application tracker then combines related emails into a single application while keeping separate roles at the same company distinct.

Previously classified emails are stored in SQLite, allowing future syncs to reuse cached results rather than repeatedly calling the LLM.

## Tech Stack

- Python
- Large Language Models (LLMs)
- Groq API
- GPT-OSS 120B
- Gmail API
- Google Sheets API
- SQLite
- OAuth 2.0
- Google API Python Client

## Project Structure

```text
EasyApply/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── easyapply/
│   ├── application_tracker.py
│   ├── classifier.py
│   ├── database.py
│   ├── email_reader.py
│   ├── email_scanner.py
│   ├── gmail_client.py
│   └── sheets_client.py
│
└── data/
    ├── easyapply.db
    └── sheet_id.txt
```

Sensitive and local files such as `.env`, `credentials.json`, `token.json`, and the `data/` directory are excluded from Git.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/sahgat11/EasyApply.git
cd EasyApply
```

### 2. Create a virtual environment

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google APIs

Create a project in Google Cloud Console and enable:

- Gmail API
- Google Sheets API

Create an OAuth 2.0 Desktop Application credential and download the client configuration.

Rename the downloaded file:

```text
credentials.json
```

and place it in the project root.

EasyApply requests access to:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/spreadsheets
```

The Gmail permission is read-only. EasyApply does not send, modify, or delete email.

### 5. Configure Groq

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_api_key_here
```

The `.env` file is excluded from Git.

## Usage

### Sync applications

```bash
python main.py sync
```

A normal sync:

1. Searches Gmail for candidate recruiting emails
2. Reuses cached classifications when available
3. Classifies only new emails
4. Rebuilds the current application state
5. Updates the Google Sheet

Example:

```text
EasyApply Sync
========================================

Sync complete
----------------------------------------
Emails scanned:       55
New emails processed: 0
Cached emails:        55
Applications tracked: 33

Google Sheet:
https://docs.google.com/spreadsheets/d/...
```

### View applications locally

```bash
python main.py list
```

Example:

```text
IBM
  Role:        Software Developer Intern 2027
  Stage:       ONLINE_ASSESSMENT
  Next Action: Complete competency assessment

DoorDash
  Role:        Software Engineer, Intern (Summer 2027) - US
  Stage:       APPLIED
  Next Action: -
```

## Application Matching

Recruiting systems often send several emails for the same application.

EasyApply normalizes company and role names and applies role-similarity logic to merge related messages.

For example:

```text
Application confirmation
        +
Coding assessment invitation
        +
Assessment reminder
        |
        v
One application:
ONLINE_ASSESSMENT
```

At the same time, separate applications to different roles at the same company remain independent.

## Structured LLM Extraction

The classifier produces structured JSON rather than free-form text.

Example:

```json
{
  "is_application_update": true,
  "company": "Example Company",
  "role": "Software Engineer Intern",
  "stage": "ONLINE_ASSESSMENT",
  "status": "ACTIVE",
  "next_action": "Complete coding assessment"
}
```

The extraction prompt restricts the model to explicitly stated information and prevents vague or invented next actions.

## Caching

LLM classifications are persisted in SQLite using the Gmail message ID as the unique identifier.

This allows EasyApply to perform incremental synchronization:

```text
First run:
55 emails -> 55 classifications

Later run:
56 emails -> 55 cached + 1 new classification
```

This reduces API usage and makes repeated syncs significantly faster.

## Google Sheets Dashboard

EasyApply automatically maintains a Google Sheets tracker containing:

```text
Company
Role
Stage
Status
Next Action
Last Updated
Emails
```

Applications are sorted by recruiting progress, with active interview and assessment stages prioritized above standard applications and closed applications.

The spreadsheet also includes formatting, filters, frozen headers, and a dashboard summarizing the current recruiting pipeline.

## Privacy

EasyApply uses Gmail's read-only API scope.

It does not send, delete, or modify email.

OAuth credentials, access tokens, API keys, the SQLite database, and application data are stored locally and excluded from the Git repository.

Email content is sent to the configured LLM provider only when a new email requires classification.

## Motivation

Internship recruiting information is often spread across dozens of emails from different applicant tracking systems and companies.

EasyApply converts those emails into a single structured source of truth while minimizing manual tracking and repeated API processing.