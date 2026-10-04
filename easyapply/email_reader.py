import base64
import html
import re
import time


def execute_with_retry(
    request,
    attempts=5
):
    for attempt in range(attempts):
        try:
            return request.execute(
                num_retries=3
            )

        except (TimeoutError, OSError):
            if attempt == attempts - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"  Gmail connection timed out. "
                f"Retrying in {wait_time}s..."
            )

            time.sleep(wait_time)


def _decode_data(data):
    if not data:
        return ""

    decoded = (
        base64
        .urlsafe_b64decode(
            data.encode("UTF-8")
        )
    )

    return decoded.decode(
        "utf-8",
        errors="ignore"
    )


def _strip_html(text):
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = html.unescape(text)

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def _extract_body(payload):
    mime_type = payload.get(
        "mimeType",
        ""
    )

    body = payload.get(
        "body",
        {}
    )

    if (
        mime_type == "text/plain"
        and body.get("data")
    ):
        return _decode_data(
            body["data"]
        )

    if (
        mime_type == "text/html"
        and body.get("data")
    ):
        return _strip_html(
            _decode_data(
                body["data"]
            )
        )

    plain_text = []
    html_text = []

    for part in payload.get(
        "parts",
        []
    ):
        text = _extract_body(
            part
        )

        if not text:
            continue

        if (
            part.get("mimeType")
            == "text/plain"
        ):
            plain_text.append(
                text
            )

        else:
            html_text.append(
                text
            )

    if plain_text:
        return "\n".join(
            plain_text
        )

    return "\n".join(
        html_text
    )


def get_email_body(
    service,
    message_id
):
    request = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
    )

    message = execute_with_retry(
        request
    )

    return _extract_body(
        message["payload"]
    ).strip()