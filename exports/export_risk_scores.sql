COPY (
    SELECT
        r.nct_id, r.termination_risk_score, r.model_version,
        t.phase, t.overall_status, t.brief_title,
        s.sponsor_name
    FROM trial_risk_scores r
    JOIN trials t ON r.nct_id = t.nct_id
    LEFT JOIN sponsors s ON t.sponsor_id = s.sponsor_id
    ORDER BY r.termination_risk_score DESC
) TO STDOUT WITH CSV HEADER;