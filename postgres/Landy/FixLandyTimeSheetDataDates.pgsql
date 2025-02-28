SELECT *
FROM LamsTimeSheets
ORDER BY Date DESC;

update LamsTimeSheets
set Date = case when Date = '04-11-2024' then '11-04-2024'
                when Date = '05-11-2024' then '11-05-2024'
                when Date = '06-11-2024' then '11-06-2024'
                when Date = '07-11-2024' then '11-07-2024'
                when Date = '08-11-2024' then '11-08-2024'
else Date end;

select case when Date = '04-11-2024' then '11-04-2024'
                when Date = '05-11-2024' then '11-05-2024'
                when Date = '06-11-2024' then '11-06-2024'
                when Date = '07-11-2024' then '11-07-2024'
                when Date = '08-11-2024' then '11-08-2024'
else Date end, *
from LamsTimeSheets;

select *
from lamstimesheets
where Date in ('11-04-2024','11-05-2024','11-06-2024','11-07-2024','11-08-2024');