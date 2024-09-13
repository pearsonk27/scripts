RISK=SSGE91-1
MAILDATE=09/11/2024
export RISK MAILDATE
grace /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/PrintOneInvoice.grc > /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/xqc
/usr2/law/src/bin/hpfilterC < /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/xqc > /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/yqc
pcl2pdf -lt:2 -letter /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/yqc /ora2/garf/Kris/Projects/MissingRenewalSolicitationInvoice_20240909/RENLTR-HHL01-A-RAS4444992-23.pdf -LOAD:/usr2/inter/src/pcl2pdf/landylogo.pcl -F:1
