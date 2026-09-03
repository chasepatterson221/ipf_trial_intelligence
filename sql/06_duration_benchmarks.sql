-- Duration benchmarks
-- Question: How long do IPF/PF trials actually take, by phase and by
-- mechanism class -- with percentile spread, not just a single average
-- that outlier trials could distort?
--
-- Only trials with both start_date and completion_date are included (i.e.
-- trials that have actually finished, one way or another -- completed,
-- terminated, or withdrawn all still have a real duration).

WITH trial_durations AS (
    SELECT
        t.nct_id,
        t.phase,
        t.overall_status,
        i.mechanism_class,
        (t.completion_date - t.start_date) AS duration_days
    FROM trials t
    JOIN interventions i ON t.nct_id = i.nct_id
    WHERE t.start_date IS NOT NULL
      AND t.completion_date IS NOT NULL
      AND t.completion_date > t.start_date  -- guard against bad/reversed date data
)

-- === Section 1: Duration benchmarks by phase ===
SELECT
    phase,
    COUNT(DISTINCT nct_id) AS trial_count,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY duration_days)) AS p25_duration_days,
    ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY duration_days)) AS median_duration_days,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY duration_days)) AS p75_duration_days,
    ROUND(AVG(duration_days)) AS avg_duration_days,
    MAX(duration_days) AS max_duration_days
FROM trial_durations
WHERE phase IN ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4')
GROUP BY phase
ORDER BY
    CASE phase
        WHEN 'EARLY_PHASE1' THEN 1
        WHEN 'PHASE1'       THEN 2
        WHEN 'PHASE2'       THEN 3
        WHEN 'PHASE3'       THEN 4
        WHEN 'PHASE4'       THEN 5
    END;


-- === Section 2: Duration benchmarks by mechanism class ===
WITH trial_durations AS (
    SELECT
        t.nct_id,
        i.mechanism_class,
        (t.completion_date - t.start_date) AS duration_days
    FROM trials t
    JOIN interventions i ON t.nct_id = i.nct_id
    WHERE t.start_date IS NOT NULL
      AND t.completion_date IS NOT NULL
      AND t.completion_date > t.start_date
)
SELECT
    mechanism_class,
    COUNT(DISTINCT nct_id) AS trial_count,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY duration_days)) AS p25_duration_days,
    ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY duration_days)) AS median_duration_days,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY duration_days)) AS p75_duration_days,
    ROUND(AVG(duration_days)) AS avg_duration_days
FROM trial_durations
GROUP BY mechanism_class
HAVING COUNT(DISTINCT nct_id) >= 5  -- same reliability filter as the success-rate query
ORDER BY median_duration_days DESC;