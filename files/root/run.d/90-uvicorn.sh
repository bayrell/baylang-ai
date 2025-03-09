if [ "`whoami`" != "root" ]; then
	echo "Script must be run as root"
	exit 1
fi

function run_uvicorn()
{
	# Setup environment
	export PYTHONDONTWRITEBYTECODE=1
	
	# Run app
	cd /app/main/Backend
	sudo -u www-data /opt/conda/bin/uvicorn server:app --reload
}

function start_uvicorn()
{
	echo "Start uvicorn"
	bash /root/run.d/90-uvicorn.sh run &
}

function stop_uvicorn()
{
	echo "Stop uvicorn"
	sudo kill `ps -aux | grep uvicorn | awk '{print $2}'`
}

case "$1" in
	run)
		run_uvicorn
	;;
	
	start)
		start_uvicorn
	;;
	
	stop)
		stop_uvicorn
	;;
	
	restart)
		stop_php_fpm
		stop_uvicorn
	;;
	
	*)
		echo "Usage: $0 {start|stop|restart}"

esac