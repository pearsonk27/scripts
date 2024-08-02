                
SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status" AS "Status",
    copro_code AS "Agent",
    'RE' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    e_mail_addr AS "Email",
    "address[1]" AS "Address1",
    "address[2]" AS "Address2",
    city AS "City",
    state AS "State",
    zip1 AS "Zip"
FROM re_icustomer
WHERE copro_code = 'LAWI001'

UNION

SELECT risk_num AS "Risk Number",
    policy_num AS "Policy Number",
    "status" AS "Status",
    copro_code AS "Agent",
    'CPA' AS "Line of Business",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    e_mail_addr AS "Email",
    "address[1]" AS "Address1",
    "address[2]" AS "Address2",
    city AS "City",
    state AS "State",
    zip1 AS "Zip"
FROM cpa_icustomer
WHERE copro_code = 'LAWI001';