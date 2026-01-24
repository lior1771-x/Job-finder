"""Streamlit UI for Job Finder."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from job_finder.storage import JobStorage
from job_finder.scrapers import SCRAPERS
from job_finder.config import Config

# Page config
st.set_page_config(
    page_title="PM Job Finder",
    page_icon="💼",
    layout="wide",
)

# Initialize storage
@st.cache_resource
def get_storage():
    config = Config.load()
    return JobStorage(config.db_path)

storage = get_storage()


def main():
    st.title("PM Job Finder")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Job Listings", "Run Scraper", "Settings"]
    )

    if page == "Dashboard":
        show_dashboard()
    elif page == "Job Listings":
        show_job_listings()
    elif page == "Run Scraper":
        show_scraper()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    st.header("Dashboard")

    # Get all jobs and filter for PM roles
    all_jobs = storage.get_all_jobs()
    pm_jobs = [j for j in all_jobs if is_product_management_role(j.title)]

    # Top-level metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("PM Jobs", len(pm_jobs))

    with col2:
        companies_with_pm = len(set(j.company for j in pm_jobs))
        st.metric("Companies with PM Roles", companies_with_pm)

    with col3:
        # PM jobs added in last 24 hours
        recent = sum(
            1 for job in pm_jobs
            if job.first_seen > datetime.now() - timedelta(days=1)
        )
        st.metric("New (24h)", recent)

    st.divider()

    # PM jobs by company chart
    st.subheader("PM Jobs by Company")

    if pm_jobs:
        from collections import Counter
        company_counts = Counter(j.company.title() for j in pm_jobs)
        df = pd.DataFrame(
            list(company_counts.items()),
            columns=["Company", "Jobs"]
        )
        df = df.sort_values("Jobs", ascending=True)
        st.bar_chart(df.set_index("Company"))
    else:
        st.info("No PM jobs in database yet. Run the scraper to fetch jobs.")


def is_product_management_role(title: str) -> bool:
    """Check if job title is a product management role."""
    title_lower = title.lower()
    pm_keywords = [
        "product manager",
        "product management",
        "product lead",
        "product owner",
        "product director",
        "head of product",
        "vp product",
        "chief product",
        "group product manager",
        "senior product manager",
        "associate product manager",
        "technical product manager",
        "staff product manager",
        "principal product manager",
    ]
    return any(kw in title_lower for kw in pm_keywords)


def show_job_listings():
    st.header("Product Management Jobs")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        companies = ["All"] + list(SCRAPERS.keys())
        selected_company = st.selectbox("Company", companies)

    with col2:
        days_filter = st.number_input(
            "Posted within (days)",
            min_value=1,
            max_value=365,
            value=7,
            help="Show jobs first seen within this many days"
        )

    with col3:
        location_filter = st.text_input("Location", placeholder="e.g. remote")

    # Fetch jobs
    if selected_company == "All":
        jobs = storage.get_all_jobs()
    else:
        jobs = storage.get_all_jobs(company=selected_company)

    # Filter for product management roles only
    jobs = [j for j in jobs if is_product_management_role(j.title)]

    # Filter by days
    cutoff_date = datetime.now() - timedelta(days=days_filter)
    jobs = [j for j in jobs if j.first_seen > cutoff_date]

    # Apply location filter
    if location_filter:
        jobs = [j for j in jobs if location_filter.lower() in j.location.lower()]

    st.write(f"Showing {len(jobs)} product management jobs from the last {days_filter} days")

    if jobs:
        # Convert to dataframe for display
        df = pd.DataFrame([
            {
                "Company": job.company.title(),
                "Title": job.title,
                "Location": job.location,
                "Department": job.department or "-",
                "First Seen": job.first_seen.strftime("%Y-%m-%d %H:%M"),
                "URL": job.url,
            }
            for job in jobs
        ])

        # Display as a table with clickable links
        st.dataframe(
            df,
            column_config={
                "URL": st.column_config.LinkColumn("Apply Link"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No jobs found matching your filters.")


def show_scraper():
    st.header("Run Scraper")

    config = Config.load()
    configured_companies = config.companies

    st.write("Select companies to scrape:")

    selected = st.multiselect(
        "Companies",
        options=list(SCRAPERS.keys()),
        default=configured_companies,
    )

    if st.button("Run Scraper", type="primary"):
        if not selected:
            st.warning("Please select at least one company.")
            return

        progress = st.progress(0)
        status = st.empty()
        results = []

        for i, company in enumerate(selected):
            status.text(f"Scraping {company}...")

            try:
                scraper = SCRAPERS[company]()
                jobs = scraper.fetch_jobs()

                # Filter for product management roles only
                jobs = [j for j in jobs if is_product_management_role(j.title)]

                # Apply location filters from config
                if config.filters.locations:
                    jobs = [j for j in jobs if j.matches_locations(config.filters.locations)]

                # Find and store new jobs
                new_jobs = storage.find_new_jobs(jobs)
                if new_jobs:
                    storage.add_jobs(new_jobs)

                results.append({
                    "company": company,
                    "total": len(jobs),
                    "new": len(new_jobs),
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "company": company,
                    "total": 0,
                    "new": 0,
                    "status": f"error: {str(e)}"
                })

            progress.progress((i + 1) / len(selected))

        status.text("Done!")

        # Show results
        st.subheader("Results")

        total_new = sum(r["new"] for r in results)
        if total_new > 0:
            st.success(f"Found {total_new} new job(s)!")
        else:
            st.info("No new jobs found.")

        results_df = pd.DataFrame(results)
        st.dataframe(results_df, hide_index=True, use_container_width=True)


def show_settings():
    st.header("Settings")

    config = Config.load()

    st.subheader("Current Configuration")

    # Display current config (read-only for now)
    st.write("**Tracked Companies:**")
    st.write(", ".join(config.companies))

    st.write("**Keyword Filters:**")
    st.write(", ".join(config.filters.keywords) if config.filters.keywords else "None")

    st.write("**Location Filters:**")
    st.write(", ".join(config.filters.locations) if config.filters.locations else "None")

    st.write("**Webhooks:**")
    slack = "Configured" if config.webhooks.slack else "Not configured"
    discord = "Configured" if config.webhooks.discord else "Not configured"
    st.write(f"Slack: {slack}, Discord: {discord}")

    st.divider()

    st.info(
        "To modify settings, edit the `config.yaml` file in your project directory. "
        "Copy `config.yaml.example` to `config.yaml` if you haven't already."
    )


if __name__ == "__main__":
    main()
