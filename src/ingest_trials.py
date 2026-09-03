"""
Ingest IPF/PF trials from ClinicalTrials.gov v2 API into PostgreSQL.
Populates: sponsors, trials tables.
"""

import requests
import psycopg2
import time

# --- Config ---
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ipf_trial_intelligence",
    "user": "ipf_user",
    "password": "ipf_pass",
    "port": 5432,
}

def is_relevant_ipf_pf_trial(condition):
    """Filter out false-positive matches like Cystic Fibrosis."""
    if not condition:
        return False
    c = condition.lower()
    if "cystic fibrosis" in c:
        return False
    if "pulmonary fibrosis" in c or c.strip() == "ipf" or "idiopathic pulmonary fibrosis" in c:
        return True
    return False

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
CONDITIONS = ["idiopathic pulmonary fibrosis", "pulmonary fibrosis"]
PAGE_SIZE = 100


def fetch_all_trials():
    """Fetch all trials matching our conditions, handling pagination."""
    all_studies = []
    seen_nct_ids = set()

    for condition in CONDITIONS:
        page_token = None
        while True:
            params = {
                "query.cond": condition,
                "pageSize": PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token

            resp = requests.get(API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

            studies = data.get("studies", [])
            for study in studies:
                nct_id = study["protocolSection"]["identificationModule"]["nctId"]
                if nct_id not in seen_nct_ids:
                    seen_nct_ids.add(nct_id)
                    all_studies.append(study)

            print(f"  [{condition}] fetched {len(studies)} (running total: {len(all_studies)})")

            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.2)  # be polite to the API

    return all_studies


def safe_get(d, *keys, default=None):
    """Safely navigate nested dicts without KeyErrors."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
        else:
            return default
    return d if d is not None else default


def parse_study(study):
    """Extract the fields we need from one study's JSON."""
    protocol = study.get("protocolSection", {})

    nct_id = safe_get(protocol, "identificationModule", "nctId")
    brief_title = safe_get(protocol, "identificationModule", "briefTitle")

    sponsor_name = safe_get(protocol, "sponsorCollaboratorsModule", "leadSponsor", "name")
    sponsor_class = safe_get(protocol, "sponsorCollaboratorsModule", "leadSponsor", "class")

    overall_status = safe_get(protocol, "statusModule", "overallStatus")
    start_date = safe_get(protocol, "statusModule", "startDateStruct", "date")
    primary_completion_date = safe_get(protocol, "statusModule", "primaryCompletionDateStruct", "date")
    completion_date = safe_get(protocol, "statusModule", "completionDateStruct", "date")
    why_stopped = safe_get(protocol, "statusModule", "whyStopped")

    study_type = safe_get(protocol, "designModule", "studyType")
    phases = safe_get(protocol, "designModule", "phases", default=[])
    phase = phases[0] if phases else None

    conditions = safe_get(protocol, "conditionsModule", "conditions", default=[])
    condition = conditions[0] if conditions else None

    enrollment_count = safe_get(protocol, "designModule", "enrollmentInfo", "count")

    interventions = safe_get(protocol, "armsInterventionsModule", "interventions", default=[])

    return {
        "nct_id": nct_id,
        "brief_title": brief_title,
        "sponsor_name": sponsor_name,
        "sponsor_class": sponsor_class,
        "overall_status": overall_status,
        "phase": phase,
        "study_type": study_type,
        "condition": condition,
        "start_date": start_date,
        "primary_completion_date": primary_completion_date,
        "completion_date": completion_date,
        "enrollment_count": enrollment_count,
        "why_stopped": why_stopped,
        "interventions": interventions,
    }


def normalize_date(date_str):
    """CT.gov sometimes gives YYYY-MM, sometimes YYYY-MM-DD. Normalize to first-of-month if needed."""
    if not date_str:
        return None
    if len(date_str) == 7:  # "YYYY-MM"
        return date_str + "-01"
    return date_str


def insert_sponsor(cur, sponsor_name, sponsor_class):
    """Insert sponsor if not exists, return sponsor_id."""
    if not sponsor_name:
        return None

    cur.execute(
        """
        INSERT INTO sponsors (sponsor_name, sponsor_class)
        VALUES (%s, %s)
        ON CONFLICT (sponsor_name) DO UPDATE SET sponsor_class = EXCLUDED.sponsor_class
        RETURNING sponsor_id
        """,
        (sponsor_name, sponsor_class),
    )
    return cur.fetchone()[0]


def insert_trial(cur, parsed, sponsor_id):
    cur.execute(
        """
        INSERT INTO trials (
            nct_id, sponsor_id, brief_title, overall_status, phase,
            study_type, condition, start_date, primary_completion_date,
            completion_date, enrollment_count, why_stopped
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (nct_id) DO NOTHING
        """,
        (
            parsed["nct_id"],
            sponsor_id,
            parsed["brief_title"],
            parsed["overall_status"],
            parsed["phase"],
            parsed["study_type"],
            parsed["condition"],
            normalize_date(parsed["start_date"]),
            normalize_date(parsed["primary_completion_date"]),
            normalize_date(parsed["completion_date"]),
            parsed["enrollment_count"],
            parsed["why_stopped"],
        ),
    )


def insert_interventions(cur, nct_id, interventions):
    for iv in interventions:
        cur.execute(
            """
            INSERT INTO interventions (nct_id, intervention_type, intervention_name)
            VALUES (%s, %s, %s)
            """,
            (nct_id, iv.get("type"), iv.get("name")),
        )


def main():
    print("Fetching trials from ClinicalTrials.gov v2 API...")
    studies = fetch_all_trials()
    print(f"\nTotal unique studies fetched: {len(studies)}\n")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for study in studies:
        parsed = parse_study(study)

        if not parsed["nct_id"]:
            skipped += 1
            continue
        
        if not is_relevant_ipf_pf_trial(parsed["condition"]):
            skipped += 1
            continue

        try:
            sponsor_id = insert_sponsor(cur, parsed["sponsor_name"], parsed["sponsor_class"])
            insert_trial(cur, parsed, sponsor_id)
            insert_interventions(cur, parsed["nct_id"], parsed["interventions"])
            inserted += 1
        except Exception as e:
            print(f"  Error on {parsed['nct_id']}: {e}")
            conn.rollback()
            skipped += 1
            continue

        conn.commit()

    cur.close()
    conn.close()

    print(f"\nDone. Inserted/updated: {inserted}, skipped: {skipped}")


if __name__ == "__main__":
    main()