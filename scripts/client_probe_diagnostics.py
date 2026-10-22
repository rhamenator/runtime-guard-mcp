"""Conservative diagnostic hints; never proof of a failed probe's cause."""
import re


def classify_limit(text):
    text = text.lower()
    if re.search(r"insufficient_quota|quota exceeded|usage limit|credit balance|billing hard limit", text):
        return "account_quota"
    if re.search(r"rate[ _-]limit|http(?: status)?[ :]+429\b|[\"'](?:httpstatuscode|status_code|status)[\"']\s*:\s*429\b", text):
        return "rate_limit"
    return "unknown"
