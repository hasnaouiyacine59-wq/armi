#!/bin/bash
while true; do
    sleep 3600
    psql "postgresql://f_api_db_user:pszvrBWJi7jklDp00Sl22YSeBUrQnRWl@dpg-d7ghdgnlk1mc73b13mgg-a.frankfurt-postgres.render.com/f_api_db" -c "TRUNCATE visits;"
done
