select expiration_date, inception_date, *
from cpa_icustomer
where policy_num IN ('ACP3677137-23','ACP3676380-23')

select policy_num, expiration_date, *
from cpa_icustomer
where expiration_date = '2024-10-24'

select expiration_date, inception_date, *
from cpa_icustomer
where risk_num in ('EARO01-1', 'BRAJ01-1');

select expiration_date, ltr2_mailed, followup_printe, folup_2yr, close_date, closeout_printe, *
from cpa_renewals_renewali
where risk_num in ('EARO01-1', 'BRAJ01-1');

select expiration_date, ltr2_mailed, followup_printe, folup_2yr, close_date, closeout_printe, *
from cpa_renewals_renewali
where risk_num in ('RAYC01-1', 'DANA01-1');

-- SELECT FROM ren WHERE ((ltr2_mailed >= $todays_date - retroDays & followup_printe = "N")  | (folup_2yr >= $todays_date - retroDays & followup_printe = "N") | (close_date >= $todays_date - retroDays & closeout_printe = "N"));