select ri.policy_num, quote_date, app_recvd_date, rc.payment, app_recvd_date, paydate, *
from re_icustomer ri
join re_checks rc on ri.risk_num = rc.risk_num
where copro_code = 'BINI001'
    and date_part('month', inception_date) = 9
    and date_part('year', inception_date) = 2024
    and pend1 is false
    and "linked_carriers[6]" is false
    and first_nv_date is null;