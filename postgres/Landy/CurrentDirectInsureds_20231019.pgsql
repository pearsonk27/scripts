SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status_cd" AS "Status",
    copro_code AS "Agent",
    'LAW' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    spec_prov_a AS "Email"
FROM law_lawyer
WHERE inception_date < now()
    AND expiration_date > now()
    AND copro_code = 'HHL01-A'

UNION

SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status" AS "Status",
    copro_code AS "Agent",
    'MISC' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    e_mail_addr AS "Email"
FROM misc_icustomer
WHERE inception_date < now()
    AND expiration_date > now()
    AND copro_code = 'HHL01-A'

UNION

SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status" AS "Status",
    copro_code AS "Agent",
    'RE' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    e_mail_addr AS "Email"
FROM re_icustomer
WHERE inception_date < now()
    AND expiration_date > now()
    AND copro_code = 'HHL01-A'

UNION

SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status" AS "Status",
    copro_code AS "Agent",
    'CPA' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    e_mail_addr AS "Email"
FROM cpa_icustomer
WHERE inception_date < now()
    AND expiration_date > now()
    AND copro_code = 'HHL01-A';

SELECT *
FROM information_schema.COLUMNS
where table_name = 'law_lawyer'
order by ordinal_position

select *
from cpa_icustomer
limit 2;