
create table LAMS_Renewal_Solicitation (
    mailstatus VARCHAR(50),
    apptype VARCHAR(50),
    state VARCHAR(10),
    riskid VARCHAR(20),
    firmname VARCHAR(255),
    effectivedate DATE,
    expirationdate DATE,
    period VARCHAR(20),
    currentpolicynumber VARCHAR(20)
)

COPY LAMS_Renewal_Solicitation
FROM '/Users/kristoferpearson/Desktop/RenewalSolicitation_01-Nov-24_14_34.csv'
WITH CSV HEADER;