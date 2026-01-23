# Job Finder

A Python tool that monitors career pages for Google, Stripe, PayPal, Uber, and Ramp, detecting new job postings and sending notifications.

## Features

- **Multi-company support**: Monitors career pages for Google, Stripe, PayPal, Uber, and Ramp
- **Smart detection**: Tracks seen jobs in SQLite database, only alerts on new postings
- **Keyword filtering**: Filter jobs by title keywords and locations
- **Multiple notifications**: Terminal output (with rich formatting) and Slack/Discord webhooks
- **Scheduled runs**: Run continuously with configurable check intervals

## Installation

```bash
# Clone the repository
cd Job-finder

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

1. **Initialize configuration:**
   ```bash
   python -m job_finder init
   ```

2. **Edit `config.yaml`** to customize filters and add webhook URLs (optional)

3. **Run a single check:**
   ```bash
   python -m job_finder run
   ```

## Usage

### Commands

```bash
# Run a single job check
python -m job_finder run

# Run scheduled checks (default: every 6 hours)
python -m job_finder schedule

# Run scheduled checks with custom interval
python -m job_finder schedule --interval 2

# Show database statistics
python -m job_finder stats

# List stored jobs
python -m job_finder list
python -m job_finder list --company stripe
python -m job_finder list --limit 20

# Test webhook connections
python -m job_finder test-webhooks

# Initialize config file
python -m job_finder init
```

### Configuration

Edit `config.yaml` to customize:

```yaml
# Webhook URLs for notifications (optional)
webhooks:
  slack: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
  discord: https://discord.com/api/webhooks/YOUR/WEBHOOK/URL

# Job filters - jobs must match at least one keyword
filters:
  keywords:
    - engineer
    - developer
    - software
  locations:  # Optional - empty list means all locations
    - remote
    - new york

# Scheduler settings
schedule:
  interval_hours: 6

# Companies to monitor
companies:
  - google
  - stripe
  - paypal
  - uber
  - ramp
```

### Environment Variables

Webhook URLs can also be set via environment variables:

```bash
export JOB_FINDER_SLACK_WEBHOOK="https://hooks.slack.com/..."
export JOB_FINDER_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
```

## How It Works

1. **Scraping**: Fetches job listings from each company's career API/page
2. **Filtering**: Applies keyword and location filters from configuration
3. **Detection**: Compares against stored jobs to find new postings
4. **Storage**: Saves new jobs to SQLite database
5. **Notification**: Outputs to terminal and sends to configured webhooks

## Data Sources

| Company | Source | Method |
|---------|--------|--------|
| Google | careers.google.com | JSON API |
| Stripe | Greenhouse | Public JSON API |
| PayPal | Workday | JSON API |
| Uber | Greenhouse | Public JSON API |
| Ramp | Lever | Public JSON API |

## Project Structure

```
job-finder/
├── job_finder/
│   ├── __init__.py
│   ├── __main__.py          # Module entry point
│   ├── main.py              # CLI and main logic
│   ├── config.py            # Configuration management
│   ├── models.py            # Job dataclass
│   ├── storage.py           # SQLite storage
│   ├── scrapers/
│   │   ├── base.py          # Abstract base scraper
│   │   ├── google.py
│   │   ├── stripe.py
│   │   ├── paypal.py
│   │   ├── uber.py
│   │   └── ramp.py
│   └── notifiers/
│       ├── terminal.py      # Rich terminal output
│       └── webhook.py       # Slack/Discord webhooks
├── config.yaml              # User configuration
├── requirements.txt
└── README.md
```

## License

MIT
