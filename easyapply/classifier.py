import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

MODEL = "openai/gpt-oss-120b"

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def classify_email(email, body):
    prompt = f"""
You classify internship application emails.

Analyze ONLY information explicitly stated in the email.
Do not guess or invent missing details.

Allowed stages:
- APPLIED
- ONLINE_ASSESSMENT
- RECRUITER_SCREEN
- TECHNICAL_INTERVIEW
- FINAL_INTERVIEW
- OFFER
- REJECTED
- WITHDRAWN
- UNKNOWN

Allowed statuses:
- ACTIVE
- CLOSED
- UNKNOWN

Rules:
1. Identify the actual employer, not Greenhouse, Ashby, Workday,
   iCIMS, Lever, Zendesk, or another recruiting platform.

2. Use the actual job title when it is stated.

3. Extract useful information from BOTH the subject and body.

4. If the subject contains:
   "Your application for ROLE at COMPANY"
   then extract ROLE and COMPANY directly.

5. "Thank you for applying" or similar confirmation:
   stage = APPLIED.

6. If the candidate is asked to complete a coding test,
   HackerRank, CodeSignal, OA, or another assessment:
   stage = ONLINE_ASSESSMENT.

7. If the email schedules or requests a recruiter conversation:
   stage = RECRUITER_SCREEN.

8. If the email schedules a technical interview:
   stage = TECHNICAL_INTERVIEW.

9. If it explicitly describes a final-round interview:
   stage = FINAL_INTERVIEW.

10. If the candidate is rejected:
    stage = REJECTED
    status = CLOSED.

11. If an offer is explicitly stated:
    stage = OFFER.

12. Never invent a next action.
    If the email does not explicitly request something,
    next_action must be null.

13. If company or role cannot be determined, use null.

14. is_application_update must be false for:
    newsletters,
    job alerts,
    advertisements,
    recommended jobs,
    networking emails,
    unrelated emails.

Return ONLY valid JSON with exactly these fields:

{{
    "is_application_update": true,
    "company": null,
    "role": null,
    "stage": "UNKNOWN",
    "status": "UNKNOWN",
    "next_action": null
}}

EMAIL

From:
{email["from"]}

Subject:
{email["subject"]}

Body:
{body[:8000]}
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise structured-data extraction system. "
                        "Never invent facts that are not present in the input."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0
        )

        response = completion.choices[0].message.content

        return json.loads(response)

    except Exception as error:
        print(f"Groq classification error: {error}")
        return None