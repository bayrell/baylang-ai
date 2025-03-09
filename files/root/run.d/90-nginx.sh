if [ "`whoami`" != "root" ]; then
  echo "Script must be run as root"
  exit 1
fi

function start_nginx()
{
	echo "Start nginx"
	/usr/sbin/nginx
}

function stop_nginx()
{
	echo "Stop nginx"
	/usr/sbin/nginx -s stop
}

function restart_nginx()
{
	echo "Restart nginx"
	/usr/sbin/nginx -s reload
}

case "$1" in
	start)
		start_nginx
	;;
	
	stop)
		stop_nginx
	;;
	
	restart)
		restart_nginx
	;;
	
	*)
		echo "Usage: $0 {start|stop|restart}"

esac