# Description

Python script detecting stall centreon engine (status.dat file not updated + zombies processes) and restarting it.

Parameter of stall detection can be overriden and an email will send when performing recovery action. Everything is also logged in syslog (or stdout if run by hand).

# Installation

```
sudo yum -y install python3-psutil
# or
sudo apt -y install python3-psutil


sudo cp -v restart_stall_centengine.py /usr/local/sbin/

sudo cp -v restart-stall-centengine.service /etc/systemd/system/
sudo cp -v restart-stall-centengine.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable restart-stall-centengine.timer
sudo systemctl start restart-stall-centengine.timer
```

# Configuration

Run `python3 restart_stall_centengine.py --help` to see available parameters and their usage:

Then you can open `restart-stall-centengine.service` file to find corresponding environment variables and set them from the override file.

For instance, you can run the following command to disable email sending on a Debian system:

```
echo 'EMAIL_ADDR=' >> /etc/default/restart-stall-centengine
```

Or to reboot the server on a RHEL system instead of restart the service:

```
echo 'ENGINE_RESTART_CMD=shutdown -r +1 "Rebooting in 1 minute, centreon engine is stall"' >> /etc/sysconfig/restart-stall-centengine
```

This new settings will be taken in account next time timer fires (next round 5 minutes).
