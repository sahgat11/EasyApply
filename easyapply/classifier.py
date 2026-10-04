import json
import os
import time

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

Status rules:
- APPLIED = ACTIVE
- ONLINE_ASSESSMENT = ACTIVE
- RECRUITER_SCREEN = ACTIVE
- TECHNICAL_INTERVIEW = ACTIVE
- FINAL_INTERVIEW = ACTIVE
- OFFER = ACTIVE
- REJECTED = CLOSED
- WITHDRAWN = CLOSED
- UNKNOWN = UNKNOWN

Rules:

1. Identify the actual employer, not Greenhouse, Ashby, Workday,
   iCIMS, Lever, Zendesk, or another recruiting platform.

2. Use the actual job title when explicitly stated.

3. Extract information from BOTH the subject and body.

4. If the subject contains:
   "Your application for ROLE at COMPANY"
   extract ROLE and COMPANY directly.

5. Application confirmation:
   stage = APPLIED
   status = ACTIVE

6. Coding test, HackerRank, CodeSignal, OA, assessment:
   stage = ONLINE_ASSESSMENT
   status = ACTIVE

7. Recruiter conversation, recruiter screen, introductory call:
   stage = RECRUITER_SCREEN
   status = ACTIVE

8. Technical interview:
   stage = TECHNICAL_INTERVIEW
   status = ACTIVE

9. Explicit final round:
   stage = FINAL_INTERVIEW
   status = ACTIVE

10. Rejection / not moving forward:
    stage = REJECTED
    status = CLOSED

11. Withdrawn application:
    stage = WITHDRAWN
    status = CLOSED

12. Explicit offer:
    stage = OFFER
    status = ACTIVE

13. Never invent next_action.

14. If no action is explicitly requested:
    next_action = null

15. Do not use vague actions such as:
    "Wait for response"
    "Review application"
    "Prepare for interview"

16. deadline must ONLY be populated if the email explicitly states
    a date or deadline for the candidate to complete an action.

17. deadline must use YYYY-MM-DD format.

18. If the email says a deadline such as:
    "October 8, 2026"
    return:
    "2026-10-08"

19. If no explicit deadline is stated:
    deadline = null

20. Do NOT infer deadlines from the email date.

21. If company or role cannot be determined, use null.

22. is_application_update = false for:
    newsletters,
    job alerts,
    advertisements,
    suggested jobs,
    career marketing,
    fellowship announcements,
    networking emails,
    unrelated emails.

Return ONLY valid JSON.

Return exactly these fields:

{{
    "is_application_update": true,
    "company": null,
    "role": null,
    "stage": "UNKNOWN",
    "status": "UNKNOWN",
    "next_action": null,
    "deadline": null
}}

EMAIL

From:
{email["from"]}

Subject:
{email["subject"]}

Body:
{body[:8000]}
"""

    for attempt in range(5):
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise structured-data extraction "
                            "system for internship recruiting emails. "
                            "Never invent facts."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_object"
                },
                temperature=0
            )

            response = (
                completion
                .choices[0]
                .message
                .content
            )

            return json.loads(response)

        except Exception as error:
            error_text = str(error)

            if (
                "429" in error_text
                and attempt < 4
            ):
                wait_time = 3 * (attempt + 1)

                print(
                    f"  Rate limit hit. "
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(wait_time)
                continue

            print(
                f"Groq classification error: "
                f"{error}"
            )

            return None