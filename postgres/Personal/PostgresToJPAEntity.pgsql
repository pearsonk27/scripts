
select '@Column(name = "' || column_name || '"' ||
    CASE WHEN character_maximum_length is null or java_type in ('LocalDate', 'Double', 'Integer', 'Boolean') then ''
        else ', length = ' || character_maximum_length end 
    || ') private ' || java_type || ' ' || lower(left(column_name, 1)) || right(replace(initcap(replace(column_name, '_', ' ')),' ', ''), -1) || ';' as java_property
from (
    select column_name,
        character_maximum_length,
        case when column_name like '%date%' then 'LocalDate'
            when column_name like 'cyber_included' or column_name like 'epl_included' then 'Boolean'
            when column_name like 'global_assets' or column_name like '%premium%' or column_name like '%revenue%' or column_name like '%deductible%' or column_name like '%TX%' or column_name like '%due%' or column_name like '%amount%' or (column_name like '%limit%' and column_name not like '%type%') then 'Double'
            when column_name like 'year_business_started' or column_name like 'employee_number' or column_name like 'installments' or column_name like 'ratable_professionals' then 'Integer'
            else java_type end as java_type,
        lower(left(column_name, 1)) || right(replace(initcap(replace(column_name, '_', ' ')),' ', ''), -1) as java_property,
        c.ordinal_position
    from information_schema.columns c
    join (
        values ('numeric', 'Double'),
            ('character varying', 'String')
    ) t(postgres_type, java_type) on t.postgres_type = c.data_type
    where table_name = 'ga_bordereaux_cpa_all'
) sub
order by ordinal_position;