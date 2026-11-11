-- Example queries for db/friction.db  (ALL DATA SYNTHETIC)
-- Run:  sqlite3 db/friction.db < sql/example_queries.sql   (or open in any SQLite browser)

-- 1. Headline numbers for the latest run
SELECT run_date, customers_analysed, customers_flagged, newly_flagged, no_longer_flagged
FROM friction_runs ORDER BY run_date DESC LIMIT 1;

-- 2. Friction category distribution (primary category)
SELECT primary_category, COUNT(*) AS customers
FROM customer_friction WHERE is_flagged = 1
GROUP BY primary_category ORDER BY customers DESC;

-- 3. Top 20 customers to work first (heuristic score, NOT a probability)
SELECT user_id, primary_category, priority_band, priority_score, data_confidence
FROM customer_friction WHERE is_flagged = 1
ORDER BY priority_score DESC, days_overdue DESC LIMIT 20;

-- 4. Newly flagged customers on the latest run vs the previous run
SELECT s.user_id, s.primary_category, s.priority_band
FROM friction_snapshot s
WHERE s.run_date = (SELECT MAX(run_date) FROM friction_runs)
  AND s.user_id NOT IN (SELECT user_id FROM friction_snapshot
                        WHERE run_date = (SELECT MAX(run_date) FROM friction_runs
                                          WHERE run_date < (SELECT MAX(run_date) FROM friction_runs)));

-- 5. Flagged customers by city and channel
SELECT city, acquisition_channel, COUNT(*) AS flagged
FROM customer_friction WHERE is_flagged = 1
GROUP BY city, acquisition_channel ORDER BY flagged DESC LIMIT 20;

-- 6. Customers to verify first (activity log contradicts funnel record)
SELECT primary_category, COUNT(*) AS verify_first
FROM customer_friction WHERE is_flagged = 1 AND data_confidence = 'LOW'
GROUP BY primary_category ORDER BY verify_first DESC;

-- 7. Support: unresolved or escalated tickets by age
SELECT t.ticket_id, t.user_id, t.category, t.priority, t.status, t.created_date
FROM tickets t
WHERE LOWER(t.status) NOT IN ('resolved','closed')
ORDER BY t.created_date LIMIT 20;

-- 8. Customers waiting more than 30 days past their normal window
SELECT user_id, primary_category, days_overdue FROM customer_friction
WHERE is_flagged = 1 AND days_overdue > 30 ORDER BY days_overdue DESC LIMIT 20;

-- 9. Registration-month view of flagged share
SELECT registration_month, COUNT(*) AS customers, SUM(is_flagged) AS flagged,
       ROUND(100.0 * SUM(is_flagged) / COUNT(*), 1) AS flagged_pct
FROM customer_friction GROUP BY registration_month ORDER BY registration_month;

-- 10. Run history
SELECT run_date, customers_flagged, newly_flagged, no_longer_flagged FROM friction_runs ORDER BY run_date;
