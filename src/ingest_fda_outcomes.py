"""
Ingest FDA approval outcomes from openFDA into PostgreSQL.
Matches on intervention (drug) name, links back to trials via interventions table.
Populates: fda_outcomes table.
"""

import requests
import psycopg2
import time
import re

DB_CONFIG = {
    "host": "localhost",
    "dbname": "ipf_trial_intelligence",
    "user": "ipf_user",
    "password": "ipf_pass",
    "port": 5432,
}

OPENFDA_BASE = "https://api.fda.gov/drug/drugsfda.json"

NON_DRUG_KEYWORDS = {
    "placebo", "vehicle", "sham", "control", "cohort",
    "untreated", "rehabilitation", "saline", "usual", "care",
    "matching", "part",
}


def normalize_drug_name(name):
    """Strip dosage/formulation noise so names match better against openFDA."""
    if not name:
        return None
    n = name.lower()
    n = re.sub(r'\d+(\.\d+)?\s*(mg|mcg|ml|g|%)', '', n)  # strip dosages
    n = re.sub(r'\(.*?\)', '', n)  # strip parentheticals
    n = re.sub(r'[^a-z\s]', '', n)  # strip punctuation
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def is_real_drug_name(name):
    """Filter out placebo/control/vehicle entries and names too short to be meaningful."""
    normalized = normalize_drug_name(name)
    if not normalized or len(normalized) < 4:
        return False
    words = set(normalized.split())
    if words & NON_DRUG_KEYWORDS:
        return False
    return True


def get_distinct_drug_names(cur):
    cur.execute("""
        SELECT DISTINCT intervention_name
        FROM interventions
        WHERE intervention_type = 'DRUG' AND intervention_name IS NOT NULL
    """)
    return [row[0] for row in cur.fetchall()]


def parse_fda_result(result):
    """Extract approval info from a single openFDA drugsfda result."""
    application_number = result.get("application_number")

    submissions = result.get("submissions", [])
    approval_date = None
    application_type = result.get("application_type")

    approved_submissions = [
        s for s in submissions
        if s.get("submission_status") == "AP"
    ]
    if approved_submissions:
        approved_submissions.sort(key=lambda s: s.get("submission_status_date", "99999999"))
        approval_date = approved_submissions[0].get("submission_status_date")
        approval_status = "APPROVED"
    else:
        approval_status = "NOT APPROVED"

    return {
        "application_number": application_number,
        "approval_status": approval_status,
        "approval_date": normalize_fda_date(approval_date),
        "application_type": application_type,
    }


def normalize_fda_date(date_str):
    """openFDA dates come as YYYYMMDD, convert to YYYY-MM-DD."""
    if not date_str or len(date_str) != 8:
        return None
    return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"


def query_openfda(normalized_name):
    """Query openFDA using an already-normalized drug name.
    Requires EXACT match (not substring) between our normalized name and
    openFDA's returned names, since loose substring matching lets in
    false-positive matches from unrelated drugs. A drug can have multiple
    FDA applications (original NDA + later generic ANDAs), so we collect
    all valid matches and return the one with the EARLIEST approval date."""
    if not normalized_name or len(normalized_name) < 4:
        return None
    if set(normalized_name.split()) & NON_DRUG_KEYWORDS:
        return None

    candidates = []

    for field in ["generic_name", "brand_name"]:
        params = {
            "search": f'openfda.{field}:"{normalized_name}"',
            "limit": 10,
        }
        try:
            resp = requests.get(OPENFDA_BASE, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                for result in results:
                    openfda = result.get("openfda", {})
                    raw_names = openfda.get(field, [])
                    for raw_name in raw_names:
                        if not raw_name:
                            continue
                        candidate_normalized = normalize_drug_name(raw_name)
                        if candidate_normalized == normalized_name:  # EXACT match only
                            candidates.append(result)
                            break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.3)

    if not candidates:
        return None

    parsed_candidates = [parse_fda_result(c) for c in candidates]
    approved = [p for p in parsed_candidates if p["approval_date"]]

    if approved:
        return min(approved, key=lambda p: p["approval_date"])
    else:
        return parsed_candidates[0]


def get_nct_ids_for_intervention(cur, intervention_name):
    cur.execute("""
        SELECT DISTINCT nct_id FROM interventions
        WHERE intervention_name = %s
    """, (intervention_name,))
    return [row[0] for row in cur.fetchall()]


def insert_fda_outcome(cur, nct_id, fda_data, matched_drug_name):
    cur.execute("""
        INSERT INTO fda_outcomes (nct_id, application_number, approval_status, approval_date, application_type, matched_drug_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        nct_id,
        fda_data["application_number"],
        fda_data["approval_status"],
        fda_data["approval_date"],
        fda_data["application_type"],
        matched_drug_name,
    ))


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    drug_names = get_distinct_drug_names(cur)
    print(f"Found {len(drug_names)} distinct drug interventions to look up.\n")

    # Group raw names by normalized form so we only query each true drug once,
    # guaranteeing every case/whitespace variant gets the identical, correct result.
    groups = {}
    for raw_name in drug_names:
        if not is_real_drug_name(raw_name):
            continue
        norm = normalize_drug_name(raw_name)
        groups.setdefault(norm, []).append(raw_name)

    skipped_non_drug = len(drug_names) - sum(len(v) for v in groups.values())
    print(f"Grouped into {len(groups)} unique normalized drug names ({skipped_non_drug} skipped as non-drug).\n")

    matched = 0
    not_found = 0
    outcomes_inserted = 0

    for i, (norm_name, raw_variants) in enumerate(groups.items(), 1):
        fda_data = query_openfda(norm_name)

        if fda_data:
            all_nct_ids = set()
            for raw_name in raw_variants:
                all_nct_ids.update(get_nct_ids_for_intervention(cur, raw_name))

            for nct_id in all_nct_ids:
                try:
                    insert_fda_outcome(cur, nct_id, fda_data, norm_name)
                    outcomes_inserted += 1
                except Exception as e:
                    print(f"  Error inserting outcome for {nct_id}: {e}")
                    conn.rollback()
                    continue
            conn.commit()
            matched += 1
            print(f"  [{i}/{len(groups)}] MATCHED: '{norm_name}' (variants: {raw_variants}) -> {fda_data['approval_status']} ({fda_data['approval_date']}, {len(all_nct_ids)} trials)")
        else:
            not_found += 1
            print(f"  [{i}/{len(groups)}] no match: '{norm_name}'")

        time.sleep(0.3)

    cur.close()
    conn.close()

    print(f"\nDone. Drugs matched: {matched}, not found: {not_found}, skipped (non-drug): {skipped_non_drug}, fda_outcomes rows inserted: {outcomes_inserted}")


if __name__ == "__main__":
    main()