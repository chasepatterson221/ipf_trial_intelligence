COPY (
    WITH phase_counts AS (
        SELECT
            phase,
            CASE phase
                WHEN 'EARLY_PHASE1' THEN 1
                WHEN 'PHASE1'       THEN 2
                WHEN 'PHASE2'       THEN 3
                WHEN 'PHASE3'       THEN 4
                WHEN 'PHASE4'       THEN 5
            END AS phase_rank,
            COUNT(*) AS trial_count
        FROM trials
        WHERE phase IN ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4')
        GROUP BY phase
    ),
    phase1_baseline AS (
        SELECT trial_count AS baseline_count FROM phase_counts WHERE phase = 'PHASE1'
    ),
    funnel AS (
        SELECT
            pc.phase, pc.phase_rank, pc.trial_count, pb.baseline_count,
            LAG(pc.trial_count) OVER (ORDER BY pc.phase_rank) AS prev_phase_count
        FROM phase_counts pc
        CROSS JOIN phase1_baseline pb
    )
    SELECT
        phase, trial_count,
        ROUND(100.0 * trial_count / baseline_count, 1) AS pct_of_phase1_baseline,
        CASE WHEN prev_phase_count IS NULL THEN NULL
             ELSE ROUND(100.0 * trial_count / prev_phase_count, 1) END AS pct_retained_vs_prev_phase
    FROM funnel
    ORDER BY phase_rank
) TO STDOUT WITH CSV HEADER;