-- Sponsor competitive ranking analysis
-- Question: Which sponsors are most active AND most successful at advancing
-- IPF/PF trials through the development pipeline?
--
-- Two scores are computed:
--   1. trial_volume: raw count of trials run by the sponsor
--   2. phase_weighted_score: sum of per-trial points, where later phases
--      score higher -- rewards sponsors whose trials progress, not just
--      sponsors who run many early-stage trials.

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
        sponsor_id,
        sponsor_name,
        sponsor_class,
        publicly_traded,
        COUNT(*) AS trial_volume,
        SUM(phase_points) AS phase_weighted_score,
        ROUND(AVG(phase_points), 2) AS avg_phase_points_per_trial
    FROM sponsor_trial_scores
    GROUP BY sponsor_id, sponsor_name, sponsor_class, publicly_traded
)
SELECT
    sponsor_name,
    sponsor_class,
    publicly_traded,
    trial_volume,
    phase_weighted_score,
    avg_phase_points_per_trial,
    RANK() OVER (ORDER BY trial_volume DESC) AS volume_rank,
    RANK() OVER (ORDER BY phase_weighted_score DESC) AS phase_weighted_rank,
    DENSE_RANK() OVER (ORDER BY phase_weighted_score DESC) AS phase_weighted_dense_rank
FROM sponsor_aggregates
WHERE trial_volume >= 2  -- filter out one-off sponsors to focus on real competitors
ORDER BY phase_weighted_score DESC
LIMIT 25;