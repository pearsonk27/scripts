SELECT *
FROM (
    SELECT RI.risk_num AS "Risk Code",
        RI.policy_num AS "Policy Number",
        RC.payment AS "Premium",
        RI.inception_date AS "Inception Date",
        RI.expiration_date AS "Expiration Date",
        RI.state AS "State",
        RI."firm_name[1]" AS "Firm Name",
        RI."address[1]" AS "Address1",
        RI."address[2]" AS "Address2",
        RI."city" AS "City",
        RI."state" AS "State",
        RI."zip1" AS "Zip",
        RI.e_mail_addr AS "Email Address",
        RI.dec_date AS "Dec Date",
        'RE' AS "Program"
    FROM re_icustomer RI
    LEFT JOIN re_checks RC ON RI.risk_num = RC.risk_num
    WHERE RI.dec_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
        AND RI.dec_date < DATE_TRUNC('month', CURRENT_DATE)
        AND RI.status = 'N'
        AND RI.policy_num IS NOT NULL
    UNION ALL
    SELECT CI.risk_num,
        CI.policy_num,
        CC.payment,
        CI.inception_date,
        CI.expiration_date,
        CI.state,
        CI."firm_name[1]",
        CI."address[1]",
        CI."address[2]",
        CI."city",
        CI."state",
        CI."zip1",
        CI.e_mail_addr,
        CI.dec_date,
        'CPA'
    FROM cpa_icustomer CI
    LEFT JOIN cpa_checks CC ON CI.risk_num = CC.risk_num
    WHERE CI.dec_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
        AND CI.dec_date < DATE_TRUNC('month', CURRENT_DATE)
        AND CI.status = 'N'
        AND CI.policy_num IS NOT NULL
    UNION ALL
    SELECT MI.risk_num,
        MI.policy_num,
        MC.payment,
        MI.inception_date,
        MI.expiration_date,
        MI.state,
        MI."firm_name[1]",
        MI."address[1]",
        MI."address[2]",
        MI."city",
        MI."state",
        MI."zip1",
        MI.e_mail_addr,
        MA.actin_date,
        'MISC'
    FROM misc_icustomer MI
    JOIN misc_accounting_acctrxi MA ON MI.risk_num = MA.actrisk
    LEFT JOIN misc_checks MC ON MI.risk_num = MC.risk_num
    WHERE MA.actin_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
        AND MA.actin_date < DATE_TRUNC('month', CURRENT_DATE)
        AND MI.status = 'N'
        AND MI.policy_num IS NOT NULL
        AND MA.actpolicy_num IS NOT NULL
    UNION ALL
    SELECT LL.risk_num,
        LL.policy_num,
        LC.payment,
        LL.inception_date,
        LL.expiration_date,
        LL.state,
        LL."firm_name[1]",
        LL.address1,
        LL.address2,
        LL."city",
        LL."state",
        LL."zip",
        LL.spec_prov_a,
        LA.actin_date,
        'LAW'
    FROM law_lawyer LL
    JOIN law_accounting_lawtrx LA ON LL.risk_num = LA.actrisk
    LEFT JOIN law_checks LC ON LL.risk_num = LC.risk_num
    WHERE LA.actin_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
        AND LA.actin_date < DATE_TRUNC('month', CURRENT_DATE)
        AND LL.status_cd = 'N'
        AND LL.policy_num IS NOT NULL
) A
ORDER BY "Program"