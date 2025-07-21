FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

RUN cd ~; \
	export DEBIAN_FRONTEND='noninteractive'; \
	apt-get update; \
	apt-get install -y --no-install-recommends apt-utils; \
	apt-get install -y --no-install-recommends mc less nano wget pv zip unzip net-tools iputils-ping sudo curl gnupg sqlite3 ca-certificates; \
	echo 'Ok'

RUN cd ~; \
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