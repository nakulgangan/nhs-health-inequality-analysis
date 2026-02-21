-- ============================================================
-- PROJECT 3: NHS Health Inequality & Service Demand Analysis
-- East Midlands Children's Palliative Care — Commissioner Reporting
-- Author: Nakul Gangan
-- ============================================================

-- ============================================================
-- SCHEMA
-- ============================================================

CREATE TABLE regions (
    region_id       VARCHAR(10) PRIMARY KEY,
    region_name     VARCHAR(40),
    imd_decile      NUMERIC(4,2),  -- Index of Multiple Deprivation (1=most deprived)
    population_u25  INT            -- Population under 25
);

CREATE TABLE referrals (
    referral_id     VARCHAR(15) PRIMARY KEY,
    region_id       VARCHAR(10) REFERENCES regions(region_id),
    referral_date   DATE,
    service_type    VARCHAR(30),
    source          VARCHAR(20),  -- 'Hospital','GP','Community','Self'
    wait_days       INT,
    outcome         VARCHAR(20)   -- 'Accepted','Declined','Withdrawn','Pending'
);

CREATE TABLE unmet_need (
    record_id       VARCHAR(15) PRIMARY KEY,
    region_id       VARCHAR(10) REFERENCES regions(region_id),
    month           DATE,
    estimated_need  NUMERIC(6,1),
    actual_served   NUMERIC(6,1)
);

-- ============================================================
-- QUERY 1: Quarterly Referral Summary — Commissioner Report
-- Aligned with NHS statutory reporting requirements
-- ============================================================
SELECT
    TO_CHAR(DATE_TRUNC('quarter', r.referral_date), 'YYYY-"Q"Q')  AS reporting_quarter,
    rg.region_name,
    COUNT(r.referral_id)                                            AS total_referrals,
    COUNT(CASE WHEN r.outcome = 'Accepted'  THEN 1 END)            AS accepted,
    COUNT(CASE WHEN r.outcome = 'Declined'  THEN 1 END)            AS declined,
    COUNT(CASE WHEN r.outcome = 'Pending'   THEN 1 END)            AS pending,
    ROUND(AVG(r.wait_days), 1)                                      AS avg_wait_days,
    ROUND(COUNT(CASE WHEN r.outcome='Accepted' THEN 1 END)::NUMERIC
          / NULLIF(COUNT(r.referral_id),0) * 100, 1)                AS acceptance_rate_pct,
    CASE
        WHEN AVG(r.wait_days) <= 14 THEN 'GREEN'
        WHEN AVG(r.wait_days) <= 21 THEN 'AMBER'
        ELSE 'RED'
    END                                                              AS wait_rag
FROM referrals r
JOIN regions rg ON r.region_id = rg.region_id
GROUP BY 1, 2
ORDER BY 1, 2;

-- ============================================================
-- QUERY 2: Deprivation vs Referral Rate Analysis
-- Evidence base for commissioners on health inequality
-- ============================================================
WITH region_stats AS (
    SELECT
        rg.region_name,
        rg.imd_decile,
        rg.population_u25,
        COUNT(r.referral_id)                                        AS total_referrals,
        ROUND(COUNT(r.referral_id)::NUMERIC / rg.population_u25 * 100000, 2) AS referral_rate_per_100k
    FROM regions rg
    LEFT JOIN referrals r ON rg.region_id = r.region_id
    GROUP BY rg.region_name, rg.imd_decile, rg.population_u25
)
SELECT
    region_name,
    imd_decile,
    total_referrals,
    referral_rate_per_100k,
    RANK() OVER (ORDER BY referral_rate_per_100k DESC)  AS need_rank,
    RANK() OVER (ORDER BY imd_decile ASC)               AS deprivation_rank
FROM region_stats
ORDER BY referral_rate_per_100k DESC;

-- ============================================================
-- QUERY 3: Unmet Need Calculation — Monthly Reporting
-- Gap between estimated population need and actual services
-- ============================================================
SELECT
    rg.region_name,
    TO_CHAR(un.month, 'YYYY-MM')                          AS month,
    un.estimated_need,
    un.actual_served,
    un.estimated_need - un.actual_served                   AS unmet_gap,
    ROUND((un.estimated_need - un.actual_served)
          / NULLIF(un.estimated_need,0) * 100, 1)          AS unmet_pct,
    CASE
        WHEN (un.estimated_need - un.actual_served)/NULLIF(un.estimated_need,0) <= 0.10 THEN 'LOW'
        WHEN (un.estimated_need - un.actual_served)/NULLIF(un.estimated_need,0) <= 0.20 THEN 'MODERATE'
        ELSE 'HIGH'
    END                                                    AS unmet_risk
FROM unmet_need un
JOIN regions rg ON un.region_id = rg.region_id
ORDER BY un.month, rg.region_name;

-- ============================================================
-- QUERY 4: Rolling 12-Month Trend
-- For ARIMA forecasting prep and trend identification
-- ============================================================
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', referral_date) AS month,
        region_id,
        COUNT(referral_id)                 AS monthly_referrals,
        ROUND(AVG(wait_days),1)            AS avg_wait
    FROM referrals
    GROUP BY 1, 2
)
SELECT
    m.month,
    rg.region_name,
    m.monthly_referrals,
    m.avg_wait,
    ROUND(AVG(m.monthly_referrals) OVER (
        PARTITION BY m.region_id
        ORDER BY m.month
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_12m_avg,
    m.monthly_referrals - LAG(m.monthly_referrals)
        OVER (PARTITION BY m.region_id ORDER BY m.month) AS mom_change
FROM monthly m
JOIN regions rg ON m.region_id = rg.region_id
ORDER BY m.month, rg.region_name;

-- ============================================================
-- QUERY 5: Data Completeness Audit — Before Commissioner Submission
-- ============================================================
SELECT
    'Referrals with NULL wait_days'    AS check_name,
    COUNT(*)                           AS affected_records,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM referrals)*100,2) AS pct_of_total
FROM referrals WHERE wait_days IS NULL

UNION ALL

SELECT 'Referrals with NULL outcome',   COUNT(*), ROUND(COUNT(*)::NUMERIC/(SELECT COUNT(*) FROM referrals)*100,2)
FROM referrals WHERE outcome IS NULL

UNION ALL

SELECT 'Referrals with future date',    COUNT(*), ROUND(COUNT(*)::NUMERIC/(SELECT COUNT(*) FROM referrals)*100,2)
FROM referrals WHERE referral_date > CURRENT_DATE

UNION ALL

SELECT 'Regions with missing IMD data', COUNT(*), NULL
FROM regions WHERE imd_decile IS NULL;
