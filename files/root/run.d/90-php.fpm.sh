if [ "`whoami`" != "root" ]; then
	echo "Script must be run as root"
	exit 1
fi

function start_php_fpm()
{
	echo "Start php-fpm"
	/usr/sbin/php-fpm8.1
}

function stop_php_fpm()
{
	echo "Stop php-fpm"
	sudo kill `ps -aux | grep php-fpm | awk '{print $2}'`
}

case "$1" in
	start)
		start_php_fpm
	;;
	
	stop)
		stop_php_fpm
	;;
	
	restart)
		stop_php_fpm
		start_php_fpm
	;;
	
	*)
		echo "Usage: $0 {start|stop|restart}"

esac