select 'RISK=' || risk_num || E'\n' ||
'MAILDATE=' || to_char(current_date, 'MM/DD/YYYY') || E'\n' ||
'AGENT=' || copro_code || E'\n' ||
'POLICY_NUM=' || policy_num
from re_icustomer
where risk_num = 'SIMT91-1';