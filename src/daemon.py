#!/usr/bin/env python
# Copyright (C) 2019 Roshan Lamichhane

# Core modules
import atexit
import os
import sys
import time
import signal


class Daemon:
    """
    A generic daemon class.
    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, home_dir='.', umask=022, verbose=1):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.home_dir = home_dir
        self.verbose = verbose
        self.umask = umask
        self.daemon_alive = True

    def daemonize(self):
        """
        Do the UNIX magic fork
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir(self.home_dir)
        os.setsid()
        os.umask(self.umask)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        if self.stderr:
            se = file(self.stderr, 'a+', 0)
        else:
            se = so
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        def sigtermhandler(signum, frame):
            self.daemon_alive = False
        signal.signal(signal.SIGTERM, sigtermhandler)
        signal.signal(signal.SIGINT, sigtermhandler)

        if self.verbose >= 1:
			print "Started"

		# Write pidfile
        atexit.register(self.delpid) # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
		os.remove(self.pidfile)

    def start(self):
		"""
		Start the daemon
		"""

		if self.verbose >= 1:
			print "Starting..."

		# Check for a pidfile to see if the daemon already runs
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
		except SystemExit:
			pid = None

		if pid:
			message = "pidfile %s already exists. Is it already running?\n"
			sys.stderr.write(message % self.pidfile)
			sys.exit(1)

		# Start the daemon
		self.daemonize()
		self.run()

    def stop(self):
		"""
		Stop the daemon
		"""

		if self.verbose >= 1:
			print "Stopping..."

		# Get the pid from the pidfile
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
		except ValueError:
			pid = None

		if not pid:
			message = "pidfile %s does not exist. Not running?\n"
			sys.stderr.write(message % self.pidfile)

			# Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
			if os.path.exists(self.pidfile):
				os.remove(self.pidfile)

			return # Not an error in a restart

		# Try killing the daemon process
		try:
			while 1:
				#os.kill(pid, signal.SIGTERM)
				os.kill(pid, signal.SIGKILL)
				time.sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print str(err)
				sys.exit(1)

		if self.verbose >= 1:
			print "Stopped"

    def restart(self):
		"""
		Restart the daemon
		"""
		self.stop()
		self.start()

    def run(self):
		"""
		You should override this method when you subclass Daemon. It will be called after the process has been
		daemonized by start() or restart().
		"""

    def running(self):
		# Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
			pid = None

        if pid is not None: return True
        else: return False

    def stopped(self):
        return not self.running()
