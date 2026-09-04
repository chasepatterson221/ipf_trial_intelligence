COPY (
    WITH sponsor_trial_scores AS (
        SELECT
            s.sponsor_id,
            s.sponsor_name,
            s.sponsor_class,
            s.publicly_traded,
            t.nct_id,
            t.phase,
            CASE t.phase
                WHEN 'EARLY_PHASE1' THEN 1
                WHEN 'PHASE1'       THEN 2
                WHEN 'PHASE2'       THEN 3
                WHEN 'PHASE3'       THEN 4
                WHEN 'PHASE4'       THEN 5
                ELSE 0
            END AS phase_points
        FROM sponsors s
        JOIN trials t ON s.sponsor_id = t.sponsor_id
    ),
    sponsor_aggregates AS (
        SELECT
            sponsor_id, sponsor_name, sponsor_class, publicly_traded,
            COUNT(*) AS trial_volume,
            SUM(phase_points) AS phase_weighted_score,
            ROUND(AVG(phase_points), 2) AS avg_phase_points_per_trial
        FROM sponsor_trial_scores
        GROUP BY sponsor_id, sponsor_name, sponsor_class, publicly_traded
    )
    SELECT
        sponsor_name, sponsor_class, publicly_traded,
        trial_volume, phase_weighted_score, avg_phase_points_per_trial,
        RANK() OVER (ORDER BY trial_volume DESC) AS volume_rank,
        RANK() OVER (ORDER BY phase_weighted_score DESC) AS phase_weighted_rank
    FROM sponsor_aggregates
    WHERE trial_volume >= 2
    ORDER BY phase_weighted_score DESC
) TO STDOUT WITH CSV HEADER;