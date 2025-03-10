if [ ! -d /data/php ]; then
	mkdir -p /data/php
	chown www-data:www-data /data/php
fi
if [ ! -d /data/php/session ]; then
	mkdir -p /data/php/session
	chown www-data:www-data /data/php/session
fi
if [ ! -d /data/php/wsdlcache ]; then
	mkdir -p /data/php/wsdlcache
	chown www-data:www-data /data/php/wsdlcache
fi
if [ ! -z $TZ ]; then
	sed -i "s|date.timezone = .*|date.timezone = $TZ|g" /etc/php83/php.ini
fi
if [ ! -z $PHP_TIME_LIMIT ]; then
	sed -i "s|php_admin_value\[max_execution_time\] = .*|php_admin_value[max_execution_time] = $PHP_TIME_LIMIT|g" /etc/php8/php-fpm.d/www.conf
	sed -i "s|max_execution_time = .*|max_execution_time = $PHP_TIME_LIMIT|g" /etc/php8/php.ini
	echo "fastcgi_read_timeout $PHP_TIME_LIMIT;" >> /etc/nginx/fastcgi_params
fi
if [ ! -z $MEMORY_LIMIT ]; then
	sed -i "s|memory_limit = .*|memory_limit = ${MEMORY_LIMIT}M|g" /etc/php8/php.ini
	sed -i "s|php_admin_value\[memory_limit\] = .*|php_admin_value[memory_limit] = ${MEMORY_LIMIT}M|g" /etc/php8/php-fpm.d/www.conf
fi
if [ ! -z $MAX_UPLOAD_SIZE ]; then
	sed -i "s|upload_max_filesize = .*|upload_max_filesize = ${MAX_UPLOAD_SIZE}M|g" /etc/php8/php.ini
	sed -i "s|php_admin_value\[upload_max_filesize\] = .*|php_admin_value[upload_max_filesize] = ${MAX_UPLOAD_SIZE}M|g" /etc/php8/php-fpm.d/www.conf
	sed -i "s|client_max_body_size .*|client_max_body_size ${MAX_UPLOAD_SIZE}m;|g" /etc/nginx/conf.d/10-connection.conf
fi
if [ ! -z $POST_MAX_SIZE ]; then
	sed -i "s|post_max_size = .*|post_max_size = ${MAX_UPLOAD_SIZE}M|g" /etc/php8/php.ini
	sed -i "s|php_admin_value\[post_max_size\] = .*|php_admin_value[post_max_size] = ${MAX_UPLOAD_SIZE}M|g" /etc/php8/php-fpm.d/www.conf
fi