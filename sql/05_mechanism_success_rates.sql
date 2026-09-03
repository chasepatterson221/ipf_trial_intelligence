-- Mechanism class success rates
-- Question: Do different drug mechanism classes succeed at different rates,
-- measured two ways -- (1) reaching Phase 3+ and (2) completing rather than
-- terminating/withdrawing?
--
-- Completion rate denominator excludes trials still in progress (RECRUITING,
-- ACTIVE_NOT_RECRUITING, NOT_YET_RECRUITING, ENROLLING_BY_INVITATION) and
-- UNKNOWN status, since those haven't had a chance to succeed or fail yet --
-- including them would artificially understate every mechanism's true rate.

WITH resolved_trials AS (
    SELECT
        t.nct_id,
        t.phase,
        t.overall_status,
        t.start_date,
        t.completion_date,
        i.mechanism_class
    FROM trials t
    JOIN interventions i ON t.nct_id = i.nct_id
    WHERE t.overall_status NOT IN (
        'RECRUITING', 'ACTIVE_NOT_RECRUITING', 'NOT_YET_RECRUITING',
        'ENROLLING_BY_INVITATION', 'UNKNOWN'
    )
),
all_phase_trials AS (
    -- Phase 3+ rate uses ALL trials with a defined phase, regardless of
    -- current status, since "did it reach phase 3" doesn't require the
    -- trial to have already finished.
    SELECT DISTINCT
        t.nct_id,
        t.phase,
        i.mechanism_class
    FROM trials t
    JOIN interventions i ON t.nct_id = i.nct_id
    WHERE t.phase IN ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4')
),
phase_success AS (
    SELECT
        mechanism_class,
        COUNT(*) AS total_phased_trials,
        SUM(CASE WHEN phase IN ('PHASE3', 'PHASE4') THEN 1 ELSE 0 END) AS phase3_plus_trials
    FROM all_phase_trials
    GROUP BY mechanism_class
),
completion_success AS (
    SELECT
        mechanism_class,
        COUNT(DISTINCT nct_id) AS total_resolved_trials,
        COUNT(DISTINCT CASE WHEN overall_status = 'COMPLETED' THEN nct_id END) AS completed_trials,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY (completion_date - start_date)
        ) AS median_duration_days
    FROM resolved_trials
    WHERE start_date IS NOT NULL AND completion_date IS NOT NULL
    GROUP BY mechanism_class
)
SELECT
    ps.mechanism_class,
    ps.total_phased_trials,
    ps.phase3_plus_trials,
    ROUND(100.0 * ps.phase3_plus_trials / ps.total_phased_trials, 1) AS phase3_plus_rate_pct,
    cs.total_resolved_trials,
    cs.completed_trials,
    ROUND(100.0 * cs.completed_trials / NULLIF(cs.total_resolved_trials, 0), 1) AS completion_rate_pct,
    ROUND(cs.median_duration_days) AS median_duration_days
FROM phase_success ps
LEFT JOIN completion_success cs ON ps.mechanism_class = cs.mechanism_class
WHERE ps.total_phased_trials >= 5  -- filter out tiny mechanism classes for statistical reliability
ORDER BY phase3_plus_rate_pct DESC;