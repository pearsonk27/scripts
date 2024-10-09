select distinct CF.*
from data_definition_column DDC
join column_conetic_forms CCF on DDC.id = CCF.column_id
join conetic_form CF on CF.id = CCF.conetic_form_id
where data_definition_id = 14;