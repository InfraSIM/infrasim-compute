'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import sys
import atexit
import tempfile
import os


def daemonize(pidfile, stdin='/dev/null', stdout='/dev/null',
              stderr='/dev/null'):
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errorno, e.strerror))
        sys.exit(1)

    os.chdir('/')
    os.umask(0)
    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errorno, e.strerror))
        sys.exit(1)

    def atexit_cb():
        try:
            os.remove(pidfile)
        except OSError:
            pass

    atexit.register(atexit_cb)

    try:
        if not os.path.exists(os.path.dirname(pidfile)):
            os.mkdir(os.path.dirname(pidfile))

        fd, nm = tempfile.mkstemp(dir=os.path.dirname(pidfile))
        os.write(fd, '%d\n' % os.getpid())
        os.close(fd)
        os.rename(nm, pidfile)
    except:
        raise

    for f in sys.stdout, sys.stderr:
        f.flush()

    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
