if [ ! -f /data/db/baylang.db ]; then
    mkdir -p /data/db
    sqlite3 /data/db/baylang.db < /root/database.sql
    chown -R www-data:www-data /data/db
fi