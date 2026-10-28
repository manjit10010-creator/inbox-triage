# Plain-code rules: free, instant, and they never see the email body.
# Domains come from your own mailbox export. Add more as you find them.

SECURITY = ("accountprotection.microsoft.com", "accounts.google.com")
JOBS = ("indeed.com", "linkedin.com", "upwork.com", "apna.co")
FINANCE = ("indusind.com", "mastertrust.co.in", "indmoney.com", "nse.co.in")
SOCIAL = ("instagram.com", "discord.com", "meetup.com")
RECEIPTS = ("rapido.bike", "flipkart.com")
SPAM_DOMAINS = ("alibaba.com", "myntra.com", "tatacliq.com")
NEWSLETTER = ("substack.com", "beehiiv.com", "medium.com")

#keyword list
SECURITY_KEYWORDS = ("security alert", "verification code", "sign-in", "sign in", "suspicious")

# Checked in this order; the first match wins.
RULES = [
    ("security_account", SECURITY),
    ("finance", FINANCE),
    ("jobs", JOBS),
    ("social", SOCIAL),
    ("receipts", RECEIPTS),
    ("spam", SPAM_DOMAINS),
    ("newsletter", NEWSLETTER),
]


def domain_matches(domain: str, bases) -> bool:
    """True if the domain is one of the bases or a subdomain of one."""
    return any(domain == b or domain.endswith("." + b) for b in bases)


def classify_by_rules(domain: str, labels: list, has_unsubscribe: bool, subject: str = ""):
    """Return a category name, or None if the email needs the AI."""
    # Security wording in the subject, but only for non-bulk mail,
    # so a newsletter about passwords doesn't trigger it.
    if not has_unsubscribe and any(k in subject.lower() for k in SECURITY_KEYWORDS):
        return "security_account"

    for category, bases in RULES:
        if domain_matches(domain, bases):
            return category
    ...

    # Fall back to Gmail's own classification
    if "CATEGORY_PROMOTIONS" in labels:
        return "promotion"
    if has_unsubscribe:
        return "newsletter"
    if "CATEGORY_UPDATES" in labels or "CATEGORY_SOCIAL" in labels:
        return "notification"

    return None  # personal or unknown: send to Gemini