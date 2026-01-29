"""Streamlit UI for Job Finder."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from job_finder.storage import JobStorage
from job_finder.scrapers import SCRAPERS
from job_finder.config import Config
from job_finder.location_utils import normalize_location, extract_search_terms

# Page config
st.set_page_config(
    page_title="PM Job Finder",
    page_icon="💼",
    layout="wide",
)

# Initialize storage - no caching to ensure latest methods are available
def get_storage():
    config = Config.load()
    return JobStorage(config.db_path)

storage = get_storage()


def main():
    st.title("PM Job Finder")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Job Listings", "My Tracker", "Run Scraper", "Settings"]
    )

    if page == "Dashboard":
        show_dashboard()
    elif page == "Job Listings":
        show_job_listings()
    elif page == "My Tracker":
        show_tracker()
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
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

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

    with col4:
        hide_tracked = st.checkbox("Hide tracked", value=False, help="Hide jobs already in tracker")

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

    # Apply location filter using normalized locations
    if location_filter:
        filter_lower = location_filter.lower()
        jobs = [j for j in jobs if filter_lower in normalize_location(j.location).lower()]

    # Get tracked jobs for marking
    tracked_jobs = storage.get_tracked_job_ids()

    # Optionally hide already tracked jobs
    if hide_tracked:
        jobs = [j for j in jobs if (j.id, j.company) not in tracked_jobs]

    st.write(f"Showing {len(jobs)} product management jobs from the last {days_filter} days")

    if jobs:
        # Display jobs with track button
        for job in jobs:
            is_tracked = (job.id, job.company) in tracked_jobs

            col1, col2 = st.columns([5, 1])

            with col1:
                # Job info
                st.markdown(f"**{job.title}**")
                # Show posted_date if available, otherwise first_seen
                if job.posted_date:
                    date_str = job.posted_date.strftime('%Y-%m-%d')
                    date_label = "Posted"
                else:
                    date_str = job.first_seen.strftime('%Y-%m-%d')
                    date_label = "Found"
                normalized_loc = normalize_location(job.location)
                st.caption(f"{job.company.title()} · {normalized_loc} · {date_label}: {date_str}")
                if job.department:
                    st.caption(f"Dept: {job.department}")

            with col2:
                if is_tracked:
                    st.success("Tracked", icon="✓")
                else:
                    if st.button("Track", key=f"track_{job.company}_{job.id}", type="primary"):
                        storage.add_tracker_entry(
                            company=job.company.title(),
                            role=job.title,
                            status="Interested",
                            job_id=job.id,
                            job_company=job.company,
                        )
                        st.rerun()

            # Apply link
            st.markdown(f"[Apply →]({job.url})")
            st.divider()
    else:
        st.info("No jobs found matching your filters.")


def show_tracker():
    st.header("My Tracker")

    # Status options
    STATUS_OPTIONS = ["Interested", "Applied", "Phone Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

    # Add new entry form
    with st.expander("Add New Entry", expanded=False):
        with st.form("add_tracker_entry"):
            col1, col2 = st.columns(2)

            with col1:
                new_company = st.text_input("Company *", placeholder="e.g. Google")
                new_role = st.text_input("Role", placeholder="e.g. Senior Product Manager")

            with col2:
                new_status = st.selectbox("Status", STATUS_OPTIONS)
                new_referral = st.text_input("Referral", placeholder="e.g. John Doe (LinkedIn)")

            new_notes = st.text_area("Notes", placeholder="Any additional notes...")

            # Link to existing job posting
            st.write("**Link to Job Posting (Optional)**")
            all_jobs = storage.get_all_jobs()
            pm_jobs = [j for j in all_jobs if is_product_management_role(j.title)]

            job_options = ["None"] + [
                f"{j.company.title()} - {j.title} ({j.id})"
                for j in pm_jobs
            ]
            selected_job = st.selectbox("Link to Job", job_options)

            submitted = st.form_submit_button("Add Entry", type="primary")

            if submitted:
                if not new_company:
                    st.error("Company is required.")
                else:
                    job_id = None
                    job_company = None
                    if selected_job != "None":
                        # Extract job_id from the selection
                        for j in pm_jobs:
                            if f"{j.company.title()} - {j.title} ({j.id})" == selected_job:
                                job_id = j.id
                                job_company = j.company
                                break

                    storage.add_tracker_entry(
                        company=new_company,
                        role=new_role if new_role else None,
                        status=new_status,
                        referral=new_referral if new_referral else None,
                        notes=new_notes if new_notes else None,
                        job_id=job_id,
                        job_company=job_company,
                    )
                    st.success(f"Added {new_company} to tracker!")
                    st.rerun()

    st.divider()

    # Display tracker entries
    entries = storage.get_all_tracker_entries()

    if not entries:
        st.info("No entries in tracker yet. Add your first company above!")
        return

    # Status summary
    status_counts = {}
    for entry in entries:
        status = entry["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    cols = st.columns(len(status_counts) if status_counts else 1)
    for i, (status, count) in enumerate(status_counts.items()):
        with cols[i % len(cols)]:
            st.metric(status, count)

    st.divider()

    # Filter by status
    filter_status = st.multiselect(
        "Filter by Status",
        STATUS_OPTIONS,
        default=[],
        placeholder="All statuses"
    )

    if filter_status:
        entries = [e for e in entries if e["status"] in filter_status]

    st.write(f"Showing {len(entries)} entries")

    # Display entries as editable cards
    for entry in entries:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.subheader(entry["company"])
                if entry["role"]:
                    st.write(f"**Role:** {entry['role']}")
                if entry["job_url"]:
                    st.markdown(f"**Linked Job:** [{entry['job_title']}]({entry['job_url']})")

            with col2:
                # Editable status
                current_status_idx = STATUS_OPTIONS.index(entry["status"]) if entry["status"] in STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=current_status_idx,
                    key=f"status_{entry['id']}"
                )

                if new_status != entry["status"]:
                    storage.update_tracker_entry(entry["id"], status=new_status)
                    st.rerun()

            with col3:
                if st.button("Delete", key=f"delete_{entry['id']}", type="secondary"):
                    storage.delete_tracker_entry(entry["id"])
                    st.rerun()

            # Expandable details
            with st.expander("Details & Edit"):
                with st.form(f"edit_{entry['id']}"):
                    edit_referral = st.text_input(
                        "Referral",
                        value=entry["referral"] or "",
                        key=f"referral_{entry['id']}"
                    )
                    edit_notes = st.text_area(
                        "Notes",
                        value=entry["notes"] or "",
                        key=f"notes_{entry['id']}"
                    )

                    # Option to link/change linked job
                    all_jobs = storage.get_all_jobs()
                    pm_jobs = [j for j in all_jobs if is_product_management_role(j.title)]
                    job_options = ["None"] + [
                        f"{j.company.title()} - {j.title} ({j.id})"
                        for j in pm_jobs
                    ]

                    current_job_idx = 0
                    if entry["job_id"]:
                        for idx, opt in enumerate(job_options):
                            if f"({entry['job_id']})" in opt:
                                current_job_idx = idx
                                break

                    edit_job = st.selectbox(
                        "Linked Job",
                        job_options,
                        index=current_job_idx,
                        key=f"job_{entry['id']}"
                    )

                    if st.form_submit_button("Save Changes"):
                        job_id = None
                        job_company = None
                        if edit_job != "None":
                            for j in pm_jobs:
                                if f"{j.company.title()} - {j.title} ({j.id})" == edit_job:
                                    job_id = j.id
                                    job_company = j.company
                                    break

                        storage.update_tracker_entry(
                            entry["id"],
                            referral=edit_referral,
                            notes=edit_notes,
                            job_id=job_id if job_id else "",
                            job_company=job_company if job_company else "",
                        )
                        st.success("Updated!")
                        st.rerun()

            st.divider()


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
