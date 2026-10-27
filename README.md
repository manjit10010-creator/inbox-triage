# Inbox Triage Assistant

An AI-powered assistant that reads incoming business messages, classifies them, drafts a suggested reply, and alerts a human when a message needs personal attention.

Built with Python and the Gemini API.

## What it does

For every new message it:

1. **Classifies** it as `sales_inquiry`, `support_request`, `spam`, or `other`
2. **Extracts** the sender's name, a one-line summary, and an urgency level (`low`, `medium`, `high`)
3. **Drafts a reply** in the sender's language, using a polite, professional tone
4. **Routes it** to one of three actions: `ignore`, `ready_for_approval`, or `human_review`
5. **Sends a Discord alert** for anything that needs a human
6. **Saves everything** to `results.csv`, and never processes the same message twice

## Safety design

Whether a message is auto-handled or held for a person is decided in **code, not by the model**:

- Spam is ignored.
- **High-urgency messages always go to a human**, even if the model says they don't need review.
- Messages containing legal threats get **no draft at all**, so nobody can approve an auto-reply by accident.
- The reply prompt forbids promising refunds, prices, or deadlines, and forbids admitting fault.
- Nothing is ever sent automatically. Drafts are suggestions for a person to approve.

## Example

| Message | Category | Urgency | Action |
|---|---|---|---|
| "We need a website with online ordering, ideally launched next month. What would it cost?" | sales_inquiry | medium | ready_for_approval |
| "My order never arrived... I want a refund TODAY." | support_request | high | human_review |
| "You've won a free prize. Click here!!!" | spam | low | ignore |
| "...this is my fifth email and I'm now contacting my lawyer." | support_request | high | human_review (no draft) |

Sample alert sent to Discord:

```
NEEDS HUMAN REVIEW (HIGH)
From: angry@example.com
Subject: Re: Re: Re: Order
Category: support_request
Summary: The sender is following up for the fifth time and threatening legal action.
Why: The message involves repeated unanswered contact and a legal threat.
```

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/manjit10010-creator/inbox-triage.git
cd inbox-triage
uv sync
```

Create a `.env` file in the project folder:

```
GEMINI_API_KEY=your-gemini-key
DISCORD_WEBHOOK_URL=your-discord-webhook-url   # optional, for alerts
```

Create your inbox file from the sample:

```bash
cp inbox.sample.csv inbox.csv        # macOS / Linux
Copy-Item inbox.sample.csv inbox.csv # Windows PowerShell
```

`inbox.csv` has the columns `id, sender, subject, body`.

## Usage

```bash
uv run triage.py
```

Results are written to `results.csv`. Running the script again skips messages that were already processed, so only new rows in `inbox.csv` use API requests.

To check your Discord webhook on its own: `uv run test_discord.py`

## Configuration

- **Model:** change the `MODEL` variable at the top of `triage.py`. Model names change often, so check the model list in Google AI Studio for what your key can use.
- **Rules and tone:** the classification and reply rules live in the prompt inside `classify_message`.
- **Routing rules:** edit `decide_action` to change what goes to a human.

## Limitations

- Messages are read from a CSV file. Gmail or form input is not implemented yet.
- Replies are drafts only, and nothing is sent.
- The free Gemini tier has low daily limits and is not meant for real customer data. Use a paid tier and review the data terms before using real messages.
- Draft language and tone can vary between runs, which is why the safety rules are enforced in code.

## Roadmap

- Gmail input
- Web form input
- Approval step before sending