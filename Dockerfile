FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

RUN cd ~; \
	export DEBIAN_FRONTEND='noninteractive'; \
	apt-get update; \
	apt-get install -y --no-install-recommends apt-utils; \
	apt-get install -y --no-install-recommends mc less nano wget pv zip unzip net-tools iputils-ping sudo curl gnupg nginx sqlite3 ca-certificates; \
	apt-get install -y --no-install-recommends php8.1 php8.1-fpm php8.1-curl php8.1-xml php8.1-xmlrpc php8.1-mysql php8.1-sqlite3 php8.1-opcache php8.1-mbstring php8.1-soap php8.1-intl php8.1-tidy; \
	echo 'Ok'

RUN cd ~; \
	sed -i 's|;date.timezone =.*|date.timezone = UTC|g' /etc/php/8.1/cli/php.ini; \
	sed -i 's|short_open_tag =.*|short_open_tag = On|g' /etc/php/8.1/cli/php.ini; \
	sed -i 's|display_errors =.*|display_errors = On|g' /etc/php/8.1/cli/php.ini; \
	sed -i 's|error_reporting =.*|display_errors = E_ALL|g' /etc/php/8.1/cli/php.ini; \
	sed -i 's|max_execution_time =.*|max_execution_time = 120|g' /etc/php/8.1/cli/php.ini; \
	sed -i 's|;date.timezone =.*|date.timezone = UTC|g' /etc/php/8.1/fpm/php.ini; \
	sed -i 's|short_open_tag =.*|short_open_tag = On|g' /etc/php/8.1/fpm/php.ini; \
	sed -i 's|display_errors =.*|display_errors = On|g' /etc/php/8.1/fpm/php.ini; \
	sed -i 's|error_reporting =.*|display_errors = E_ALL|g' /etc/php/8.1/fpm/php.ini; \
	sed -i 's|max_execution_time =.*|max_execution_time = 30|g' /etc/php/8.1/fpm/php.ini; \
	sed -i 's|listen =.*|listen = /var/run/php-fpm.sock|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|;clear_env =.*|clear_env = no|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|;catch_workers_output =.*|catch_workers_output = yes|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|pm.max_children = .*|pm.max_children = 10|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|pm.start_servers = .*|pm.start_servers = 1|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|pm.min_spare_servers = .*|pm.min_spare_servers = 1|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	sed -i 's|pm.max_spare_servers = .*|pm.max_spare_servers = 2|g' /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[error_log] = /var/log/nginx/php_error.log' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[memory_limit] = 128M' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[post_max_size] = 128M' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[upload_max_filesize] = 128M' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[file_uploads] = on' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[upload_tmp_dir] = /tmp' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[precision] = 16' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[max_execution_time] = 30' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[session.save_path] = /data/php/session' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	echo 'php_admin_value[soap.wsdl_cache_dir] = /data/php/wsdlcache' >> /etc/php/8.1/fpm/pool.d/www.conf; \
	ln -sf /dev/stdout /var/log/nginx/access.log; \
	ln -sf /dev/stderr /var/log/nginx/error.log; \
	ln -sf /dev/stderr /var/log/nginx/php_error.log; \
	chown www-data:www-data /var/log/nginx; \
	echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/wheel; \
	groupadd -r wheel; \
	usermod -a -G wheel www-data; \
    addgroup --gid 1000 user; \
    adduser --uid 1000 --gid 1000 --home /data/home --shell /bin/bash --gecos user \
		--disabled-password -q user; \
    usermod -a -G wheel user; \
    usermod -a -G www-data user; \
	echo 'Ok'

ADD files/root/requirements.txt /root/requirements.txt
RUN cd ~; \
    /opt/conda/bin/pip install -r /root/requirements.txt; \
	rm -rf /root/.cache/pip; \
    echo "Ok"

RUN cd ~; \
	mkdir /app; \
    chown 1000:1000 /app; \
    echo "Ok"

ADD files /
ADD src /app
USER user
WORKDIR /data/home
ENTRYPOINT ["/root/entrypoint.sh"]
CMD ["/root/run.sh"]