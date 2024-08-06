-- Risk code, Policy Number, Policy Term, State, Insured name , address, and email address 

SELECT risk_num AS "Risk Code",
    policy_num AS "Policy Number",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    state AS "State",
    "firm_name[1]" AS "Firm Name",
    "address[1]" AS "Address1",
    "address[2]" AS "Address2",
    "city" AS "City",
    "state" AS "State",
    "zip1" AS "Zip",
    e_mail_addr AS "Email Address"
FROM re_icustomer
WHERE inception_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND inception_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
  AND status = 'N'
  AND policy_num IS NOT NULL
UNION ALL
SELECT risk_num AS "Risk Code",
    policy_num AS "Policy Number",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    state AS "State",
    "firm_name[1]" AS "Firm Name",
    "address[1]" AS "Address1",
    "address[2]" AS "Address2",
    "city" AS "City",
    "state" AS "State",
    "zip1" AS "Zip",
    e_mail_addr AS "Email Address"
FROM cpa_icustomer
WHERE inception_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND inception_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
  AND status = 'N'
  AND policy_num IS NOT NULL
UNION ALL
SELECT risk_num AS "Risk Code",
    policy_num AS "Policy Number",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    state AS "State",
    "firm_name[1]" AS "Firm Name",
    "address[1]" AS "Address1",
    "address[2]" AS "Address2",
    "city" AS "City",
    "state" AS "State",
    "zip1" AS "Zip",
    e_mail_addr AS "Email Address"
FROM misc_icustomer
WHERE inception_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND inception_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
  AND status = 'N'
  AND policy_num IS NOT NULL
UNION ALL
SELECT risk_num AS "Risk Code",
    policy_num AS "Policy Number",
    inception_date AS "Inception Date",
    expiration_date AS "Expiration Date",
    state AS "State",
    "firm_name[1]" AS "Firm Name",
    address1 AS "Address1",
    address2 AS "Address2",
    "city" AS "City",
    "state" AS "State",
    "zip" AS "Zip",
    spec_prov_a AS "Email Address"
FROM law_lawyer
WHERE inception_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND inception_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
  AND status_cd = 'N'
  AND policy_num IS NOT NULL;