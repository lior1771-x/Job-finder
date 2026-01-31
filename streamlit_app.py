"""Streamlit UI for Job Finder."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from job_finder.storage import JobStorage
from job_finder.scrapers import SCRAPERS
from job_finder.config import Config
from job_finder.location_utils import normalize_location, extract_search_terms
from job_finder.matching import score_jobs

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
        ["Dashboard", "Job Listings", "My Tracker", "Referrals", "Settings"]
    )

    if page == "Dashboard":
        show_dashboard()
    elif page == "Job Listings":
        show_job_listings()
    elif page == "My Tracker":
        show_tracker()
    elif page == "Referrals":
        show_referrals()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    st.header("Dashboard")

    config = Config.load()

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

    from collections import Counter
    company_counts = Counter(j.company.title() for j in pm_jobs)

    # Include all configured companies, even those with 0 jobs
    all_company_names = [
        SCRAPERS[key].company_name
        for key in config.companies
        if key in SCRAPERS
    ]
    for name in all_company_names:
        if name not in company_counts:
            company_counts[name] = 0

    if any(v > 0 for v in company_counts.values()):
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

    # Map display names to scraper keys
    company_display_names = {cls.company_name: key for key, cls in SCRAPERS.items()}

    # Scraper section
    config = Config.load()
    with st.expander("Scrape New Jobs"):
        scraper_col1, scraper_col2 = st.columns([4, 1])

        with scraper_col1:
            selected_scrapers = st.multiselect(
                "Companies to scrape",
                options=list(company_display_names.keys()),
                default=[
                    name for name, key in company_display_names.items()
                    if key in config.companies
                ],
            )

        with scraper_col2:
            st.write("")  # spacing
            run_scraper = st.button("Scrape", type="primary", use_container_width=True)

        clear_rescrape = st.checkbox("Clear existing data before scraping", value=False,
                                      help="Deletes stored jobs for selected companies, then re-scrapes fresh")

        if run_scraper:
            if not selected_scrapers:
                st.warning("Please select at least one company.")
            else:
                progress = st.progress(0)
                status_text = st.empty()
                results = []

                for i, name in enumerate(selected_scrapers):
                    key = company_display_names[name]
                    status_text.text(f"Scraping {name}...")

                    try:
                        scraper = SCRAPERS[key]()

                        if clear_rescrape:
                            # Delete by both display name and scraper company_name
                            deleted = storage.delete_jobs_by_company(name)
                            deleted += storage.delete_jobs_by_company(scraper.company_name)
                            deleted += storage.delete_jobs_by_company(key)
                            st.info(f"Cleared {deleted} old {name} jobs")

                        jobs = scraper.fetch_jobs()

                        jobs = [j for j in jobs if is_product_management_role(j.title)]

                        if config.filters.locations:
                            jobs = [j for j in jobs if j.matches_locations(config.filters.locations)]

                        new_jobs = storage.find_new_jobs(jobs)
                        if new_jobs:
                            storage.add_jobs(new_jobs)

                        results.append({"Company": name, "PM Jobs": len(jobs), "New": len(new_jobs), "Status": "OK"})
                    except Exception as e:
                        results.append({"Company": name, "PM Jobs": 0, "New": 0, "Status": f"Error: {e}"})

                    progress.progress((i + 1) / len(selected_scrapers))

                status_text.text("Done!")
                total_new = sum(r["New"] for r in results)
                if total_new > 0:
                    st.success(f"Found {total_new} new job(s)!")
                else:
                    st.info("No new jobs found.")
                st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)

    st.divider()

    # Filters
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        companies = ["All"] + list(company_display_names.keys())
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

    # Compute match scores if resume is available
    resume = storage.get_latest_resume()
    match_scores = {}
    if resume:
        match_scores = score_jobs(resume["text_content"], jobs)

    st.write(f"Showing {len(jobs)} product management jobs from the last {days_filter} days")

    if jobs:
        # Display jobs with track button
        for job in jobs:
            is_tracked = (job.id, job.company) in tracked_jobs
            match = match_scores.get((job.id, job.company))

            col1, col2 = st.columns([5, 1])

            with col1:
                # Job title with match badge
                title_text = f"**{job.title}**"
                if match and match.level != "N/A":
                    if match.level == "Strong":
                        title_text += f" &nbsp; :green[**Strong Match** ({match.score}%)]"
                    elif match.level == "Good":
                        title_text += f" &nbsp; :orange[**Good Match** ({match.score}%)]"
                    else:
                        title_text += f" &nbsp; :gray[Low Match ({match.score}%)]"
                st.markdown(title_text)
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
                    st.success("Tracked")
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
                            notes=edit_notes,
                            job_id=job_id if job_id else "",
                            job_company=job_company if job_company else "",
                        )
                        st.success("Updated!")
                        st.rerun()

            st.divider()


def show_referrals():
    st.header("Referrals")

    # Add referral form
    with st.expander("Add Referral", expanded=False):
        with st.form("add_referral"):
            col1, col2 = st.columns(2)

            with col1:
                ref_name = st.text_input("Name *", placeholder="e.g. Jane Smith")
                ref_company = st.text_input("Company *", placeholder="e.g. Google")

            with col2:
                ref_contact = st.text_input("Contact", placeholder="e.g. email, LinkedIn URL, phone")

            ref_notes = st.text_area("Notes", placeholder="How you know them, context, etc.")

            # Link to existing job posting
            st.write("**Link to Job Posting (Optional)**")
            all_jobs = storage.get_all_jobs()
            pm_jobs = [j for j in all_jobs if is_product_management_role(j.title)]
            job_options = ["None"] + [
                f"{j.company.title()} - {j.title} ({j.id})"
                for j in pm_jobs
            ]
            selected_job = st.selectbox("Link to Job", job_options, key="ref_link_job")

            submitted = st.form_submit_button("Add Referral", type="primary")

            if submitted:
                if not ref_name:
                    st.error("Name is required.")
                elif not ref_company:
                    st.error("Company is required.")
                else:
                    job_id = None
                    job_company = None
                    if selected_job != "None":
                        for j in pm_jobs:
                            if f"{j.company.title()} - {j.title} ({j.id})" == selected_job:
                                job_id = j.id
                                job_company = j.company
                                break

                    storage.add_referral(
                        name=ref_name,
                        company=ref_company,
                        contact=ref_contact if ref_contact else None,
                        notes=ref_notes if ref_notes else None,
                        job_id=job_id,
                        job_company=job_company,
                    )
                    st.success(f"Added referral: {ref_name} at {ref_company}")
                    st.rerun()

    st.divider()

    # Display referrals
    referrals = storage.get_all_referrals()

    if not referrals:
        st.info("No referrals yet. Add your first referral above!")
        return

    # Summary: count by company
    from collections import Counter
    company_counts = Counter(r["company"] for r in referrals)
    cols = st.columns(min(len(company_counts), 4))
    for i, (company, count) in enumerate(company_counts.most_common()):
        with cols[i % len(cols)]:
            st.metric(company, count)

    st.divider()
    st.write(f"Showing {len(referrals)} referrals")

    # Display referral cards
    for ref in referrals:
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.subheader(ref["name"])
                st.write(f"**Company:** {ref['company']}")
                if ref["contact"]:
                    st.write(f"**Contact:** {ref['contact']}")
                if ref["job_url"]:
                    st.markdown(f"**Linked Job:** [{ref['job_title']}]({ref['job_url']})")

            with col2:
                if st.button("Delete", key=f"del_ref_{ref['id']}", type="secondary"):
                    storage.delete_referral(ref["id"])
                    st.rerun()

            # Expandable edit form
            with st.expander("Edit"):
                with st.form(f"edit_ref_{ref['id']}"):
                    edit_name = st.text_input("Name", value=ref["name"], key=f"rname_{ref['id']}")
                    edit_company = st.text_input("Company", value=ref["company"], key=f"rcompany_{ref['id']}")
                    edit_contact = st.text_input("Contact", value=ref["contact"] or "", key=f"rcontact_{ref['id']}")
                    edit_notes = st.text_area("Notes", value=ref["notes"] or "", key=f"rnotes_{ref['id']}")

                    # Job link
                    all_jobs = storage.get_all_jobs()
                    pm_jobs = [j for j in all_jobs if is_product_management_role(j.title)]
                    job_options = ["None"] + [
                        f"{j.company.title()} - {j.title} ({j.id})"
                        for j in pm_jobs
                    ]

                    current_job_idx = 0
                    if ref["job_id"]:
                        for idx, opt in enumerate(job_options):
                            if f"({ref['job_id']})" in opt:
                                current_job_idx = idx
                                break

                    edit_job = st.selectbox(
                        "Linked Job",
                        job_options,
                        index=current_job_idx,
                        key=f"rjob_{ref['id']}"
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

                        storage.update_referral(
                            ref["id"],
                            name=edit_name,
                            company=edit_company,
                            contact=edit_contact,
                            notes=edit_notes,
                            job_id=job_id if job_id else "",
                            job_company=job_company if job_company else "",
                        )
                        st.success("Updated!")
                        st.rerun()

            st.divider()


def show_settings():
    st.header("Settings")

    config = Config.load()

    # Resume upload section
    st.subheader("Resume")

    resume = storage.get_latest_resume()
    if resume:
        st.success(f"Resume uploaded: **{resume['filename']}** (uploaded {resume['uploaded_at'][:10]})")
    else:
        st.info("No resume uploaded yet. Upload a PDF to enable job matching.")

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    if uploaded_file is not None:
        try:
            from PyPDF2 import PdfReader
            import io

            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            text = text.strip()
            if text:
                storage.add_resume(uploaded_file.name, text)
                st.success(f"Resume '{uploaded_file.name}' uploaded and processed ({len(text)} characters extracted).")
                st.rerun()
            else:
                st.error("Could not extract text from the PDF. Please try a different file.")
        except Exception as e:
            st.error(f"Error processing PDF: {e}")

    st.divider()

    st.subheader("Current Configuration")

    # Display current config (read-only for now)
    st.write("**Tracked Companies:**")
    # Show display names instead of scraper keys
    company_names = [
        SCRAPERS[key].company_name if key in SCRAPERS else key
        for key in config.companies
    ]
    st.write(", ".join(company_names))

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
