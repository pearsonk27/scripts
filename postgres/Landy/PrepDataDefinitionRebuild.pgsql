
drop table column_conetic_forms;
drop table data_definition_column;
drop table conetic_form;
drop table data_definition;

drop sequence data_definition_id_seq;
drop sequence conetic_form_id_seq;
drop sequence data_definition_column_id_seq;
drop sequence column_conetic_form_id_seq;

delete from databasechangelog
where id in ('create-sequence-data-definition-id-seq',
    'create_table_data_definition',
    'create-sequence-conetic-form-id-seq',
    'create_table_conetic_form',
    'create-sequence-data-definition-column-id-seq',
    'create_table_data_definition_column',
    'create-sequence-column-conetic-form-id-seq',
    'create_table_column_conetic_form');