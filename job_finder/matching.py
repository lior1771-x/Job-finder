"""Resume-to-JD keyword matching for job postings."""

import re
from dataclasses import dataclass
from typing import List, Optional

# Curated PM-relevant skills and keywords for better matching
PM_SKILL_KEYWORDS = [
    # Core PM skills
    "product management", "product strategy", "product roadmap", "roadmap",
    "product vision", "product lifecycle", "product development",
    "product discovery", "product analytics", "product ops",
    # Leadership & collaboration
    "stakeholder management", "cross-functional", "leadership",
    "team management", "executive communication", "influence without authority",
    # Methodologies
    "agile", "scrum", "kanban", "lean", "waterfall", "safe",
    "design thinking", "jobs to be done", "jtbd",
    # Analysis & data
    "data analysis", "data-driven", "sql", "a/b testing", "ab testing",
    "experimentation", "hypothesis", "metrics", "kpis", "okrs",
    "quantitative", "qualitative", "user research", "market research",
    "competitive analysis", "business analysis",
    # Technical
    "api", "apis", "saas", "b2b", "b2c", "platform", "infrastructure",
    "machine learning", "ml", "ai", "artificial intelligence",
    "cloud", "aws", "gcp", "azure", "microservices", "system design",
    "technical requirements", "prd", "product requirements",
    "specifications", "spec", "technical specification",
    # UX & Design
    "user experience", "ux", "ui", "user interface", "wireframes",
    "prototyping", "usability", "accessibility", "figma",
    "user stories", "user flows", "journey mapping",
    # Business
    "go-to-market", "gtm", "pricing", "monetization", "revenue",
    "growth", "acquisition", "retention", "engagement", "conversion",
    "funnel", "p&l", "business case", "roi", "market sizing", "tam",
    # Communication
    "presentations", "documentation", "storytelling",
    "requirements gathering", "sprint planning", "backlog",
    "prioritization", "trade-offs", "decision making",
    # Tools
    "jira", "confluence", "asana", "notion", "linear",
    "amplitude", "mixpanel", "tableau", "looker", "google analytics",
    "salesforce", "hubspot",
    # Industry
    "fintech", "payments", "e-commerce", "ecommerce", "healthcare",
    "enterprise", "marketplace", "security", "compliance",
]

# Common English stop words to filter out
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "were",
    "are", "been", "has", "had", "have", "do", "did", "does", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "his", "her", "they", "their", "them", "its",
    "not", "no", "so", "if", "then", "than", "also", "just", "about",
    "up", "out", "all", "more", "some", "such", "into", "over", "after",
    "before", "between", "through", "during", "each", "very", "most",
    "other", "own", "same", "both", "only", "new", "work", "working",
    "ability", "able", "experience", "including", "well", "strong",
    "team", "role", "company", "job", "position", "candidate",
    "responsibilities", "requirements", "qualifications", "years",
    "etc", "e.g", "i.e",
}


@dataclass
class MatchResult:
    """Result of matching a resume against a job description."""
    score: int  # 0-100
    level: str  # "Strong", "Good", "Low", "N/A"
    matched_keywords: List[str]


def extract_keywords(text: str) -> set:
    """Extract meaningful keywords and phrases from text."""
    text_lower = text.lower()
    keywords = set()

    # First, find multi-word PM skill matches
    for skill in PM_SKILL_KEYWORDS:
        if skill in text_lower:
            keywords.add(skill)

    # Then extract single words (excluding stop words and short tokens)
    words = re.findall(r"[a-z][a-z\-]+", text_lower)
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            keywords.add(word)

    return keywords


def score_job(resume_text: str, job_description: str) -> MatchResult:
    """Score how well a resume matches a job description."""
    if not job_description:
        return MatchResult(score=0, level="N/A", matched_keywords=[])

    resume_keywords = extract_keywords(resume_text)
    jd_keywords = extract_keywords(job_description)

    if not resume_keywords or not jd_keywords:
        return MatchResult(score=0, level="N/A", matched_keywords=[])

    # Find keywords present in both resume and JD
    matched = resume_keywords & jd_keywords

    # Score: what fraction of JD keywords are covered by the resume
    score = round(len(matched) / len(jd_keywords) * 100)
    score = min(score, 100)

    if score >= 70:
        level = "Strong"
    elif score >= 40:
        level = "Good"
    else:
        level = "Low"

    return MatchResult(
        score=score,
        level=level,
        matched_keywords=sorted(matched),
    )


def score_jobs(resume_text: str, jobs) -> dict:
    """Score multiple jobs against a resume. Returns dict of (job.id, job.company) -> MatchResult."""
    results = {}
    for job in jobs:
        result = score_job(resume_text, job.description or "")
        results[(job.id, job.company)] = result
    return results
