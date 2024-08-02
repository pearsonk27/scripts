select *
from re_icustomer
where expiration_date - 7 <= '2024-06-27'
    and '2024-06-27' < expiration_date;

select *
from re_renewals_renewali rrr
join re_icustomer ri on rrr.risk_num = ri.risk_num
where (close_date = '2024-06-27'
    or rrr.expiration_date - 7 <= '2024-06-27'
        and '2024-06-27' < rrr.expiration_date)
    and rrr."flags[1]" = false
    and (ri.status = 'N' or ri.status = 'R')
    and ri.pad4 = 'N'
    and ri.state != 'FL'
    and app_recvd_date < ltr1_mailed
    and ri.copro_code = 'HHL01-A';

select app_recvd_date, ltr1_mailed, *
from re_renewals_renewali rrr
join re_icustomer ri on rrr.risk_num = ri.risk_num
where rrr.expiration_date - 7 = '2024-06-27'
    and rrr."flags[1]" = false
    and (ri.status = 'N' or ri.status = 'R')
    and ri.pad4 = 'N'
    and ri.state != 'FL'
    and app_recvd_date < ltr1_mailed
    and ri.copro_code = 'HHL01-A';

select *
from re_renewals_renewali
where expiration_date - 7 = '2024-06-27';

/*

((close_date = $todays_date | ($todays_date >= expiration_date - 7 & $todays_date < expiration_date)) & flags[1] = "N")

   FIND cust WHERE cust.risk_num = ren.risk_num;
   IF ((status = "N" | status = "R") & cust.pad4 = "N")
	x = x;
   ELSE
    RETURN;

   IF state = "FL"
      RETURN;
   IF app_recvd_date > ltr1_mailed
      RETURN;
   FIND check WHERE check.risk_num = cust.risk_num;
   IF ERROR(check)
      paydate = "";
   FIND copro WHERE cpcode = copro_code;
   IF cpdca != "D"
      RETURN;

*/