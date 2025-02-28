
create table directlogin (
    email VARCHAR(255),
    password VARCHAR(255),
    policynum VARCHAR(20),
    polmonth VARCHAR(10),
    polyear INT,
    secid INT
)

COPY directlogin
FROM '/Volumes/pdf_files/garf/Kris/Projects/AppraiserOnlineTransferFail_20241202/directlogin.csv'
WITH CSV HEADER;