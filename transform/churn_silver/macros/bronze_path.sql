{% macro bronze_path(table_name) %}
  read_parquet('{{ project_root() }}/../../data/bronze/{{ table_name }}/**/*.parquet')
{% endmacro %}

{% macro project_root() %}
  {{ modules.os.path.abspath(project.project_root) }}
{% endmacro %}
