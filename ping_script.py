#!/usr/bin/python3
import subprocess
import threading
import argparse
import curses
import signal
import socket
import queue
import shlex
import math
import time
import sys

PING_HOSTS = []
PING_NAMES = []

CURL_HOSTS = []
CURL_NAMES = []
HTTPS_HOSTS = []
HTTPS_NAMES = []
PING_LOCKS = []
CURL_LOCKS = []
PING_RESULTS = []
CURL_RESULTS = []
WORKERS = []
INTERVAL = 0.5

def stderr(*strings, **kwargs):
    sys.stdout.flush()
    for s in strings:
        sys.stderr.write(str(s) + ' ')
    sys.stderr.write('\b\n')
    sys.stderr.flush()

class WorkerThread(threading.Thread):
    def __init__(self, host, name, lock, result, ping=True, interval=INTERVAL):
        threading.Thread.__init__(self)
        self.host = host
        self.name = name
        self.lock = lock
        self.result = result
        self.ping = ping
        self.interval = interval
        self.success = 0
        self.oldsuccess = 0
        self.fail = 0
        self.oldfail = 0
        self.code = ''  # the last return code we got
    def rotateResult(self):
        for i in range(1,len(self.result)):
            self.result[i-1] = self.result[i]
    def addResult(self, value):
        self.lock.acquire()
        if len(self.result) >= 10:
            self.rotateResult()
            self.result[len(self.result)-1] = value
        else:
            self.result.append(value)
        self.lock.release()
    def run(self):
        startTime = 0
        while True:
            if time.time() - startTime < self.interval:
                time.sleep(max(0,self.interval - (time.time() - startTime)))
            startTime = time.time()
            if self.ping:
                commandLine = "/bin/ping -W 1 -c 1 %s" %(self.host)
                sub = subprocess.Popen(shlex.split(commandLine), stdout=subprocess.PIPE)
                time.sleep(0.05)
                if sub.poll() == None:
                    #process has not termintaed yet.
                    time.sleep(self.interval-(0.05*2))
                    if sub.poll() == None:
                        sub.terminate()
                (stdout, stderr) = sub.communicate()
                stdout = str(stdout, 'ascii')
                lines = stdout.split('\n')
                resultAdded = False
                for line in lines:
                    if "rtt" in line:
                        self.success += 1
                        self.code = 'OK'
                        resultAdded = True
                        parts = line.split()
                        numbers = parts[3].split('/')
                        value = '{0:.1f}'.format(float(numbers[0]))
                        self.addResult(value)
                        #self.oldfail = self.fail
                        break
                if not resultAdded:
                    self.addResult('.')
                    self.fail += 1
                    self.code = 'FAIL'
                    #curses.beep()
            else:
                # curl command: curl -s -m 1 --output /dev/null -w "%{http_code} %{time_total}" www.odu.edu
                commandLine = "curl -s -m 1 --output /dev/null -w \"%%{http_code} %%{time_total}\" %s" %(self.host)
                sub = subprocess.Popen(shlex.split(commandLine), stdout=subprocess.PIPE)
                (stdout, stderr) = sub.communicate()
                stdout = str(stdout, 'ascii')
                lines = stdout.split('\n')
                parts = lines[0].split()
                response = int(parts[0])
                self.code = parts[0]
                if response == 200:
                    self.success += 1
                    self.addResult(int(float(parts[1])*1000))
                    #self.oldfail = self.fail
                else:
                    self.addResult('.')
                    self.fail += 1
    def resultString(self):
        return str(self.result).replace(',','')
    
def sigint_handler(signal, frame):
    y = 0
    contents = ''
    while True:
        temp = str(stdscr.instr(y,0),'ascii')
        if temp[0] is ' ':
            break
        contents += temp
        y+=1
    curses.nocbreak();
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()
    #print contents
    exit(0)

def addWorkerString(stdscr, worker):
    alert=False
    if worker.ping:
        stdscr.addstr("ping", curses.color_pair(3))
    else:
        stdscr.addstr("http", curses.color_pair(2))
    stdscr.move(stdscr.getyx()[0],5)
    stdscr.addstr(worker.host)
    stdscr.addstr(" " + worker.name, curses.color_pair(4))
    #stdscr.move(stdscr.getyx()[0],19)
    #stdscr.addstr("from " + worker.int)
    stdscr.move(stdscr.getyx()[0], maxWidth)
    stdscr.addstr(str(worker.success))
    stdscr.move(stdscr.getyx()[0], maxWidth+6)
    if worker.oldfail != worker.fail:
        alert = True
        worker.oldfail = worker.fail
        worker.oldsuccess = worker.success
    if worker.oldsuccess == worker.success:
        stdscr.addstr(str(worker.fail), curses.A_BOLD | curses.color_pair(1))
    else:
        stdscr.addstr(str(worker.fail))
    # erase old code
    stdscr.move(stdscr.getyx()[0],maxWidth+11)
    stdscr.addstr('     ')
    # write new code
    stdscr.move(stdscr.getyx()[0],maxWidth+11)
    stdscr.addstr(worker.code)
    x=maxWidth+11
    for res in worker.result:
        x+=5
        stdscr.move(stdscr.getyx()[0], x)
        stdscr.addstr(str(res) + '    ')
    return alert

def parseArgs():
    description = "Ping hosts and record results."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("ping_target", nargs="*", help="Hostname or address to ping")
    parser.add_argument("-w", "--www-target", action="append", metavar="www-target", help="Hostname or address to curl")
    parser.add_argument("-s", "--https-target", action="append", metavar="https-target", help="Hostname or address to curl (https)")
    parser.add_argument("-i", "--action-interval", type=int, metavar='millis', help="Time between pings/curls in milliseconds")
    args = parser.parse_args()
    #print(args)
    if not args.ping_target and not args.www_target and not args.https_target:
        parser.error("You must specify at least one ping or curl target")
    return args

args = parseArgs()
if args.ping_target:
    for name in args.ping_target:
        try:
            ip = socket.gethostbyname(name)
        except:
            stderr("Error resolving name:", name)
            sys.exit(3)
        PING_HOSTS.append(ip)
        PING_NAMES.append(name)
if args.www_target:
    for name in args.www_target:
        try:
            ip = socket.gethostbyname(name)
        except:
            stderr("Error resolving name:", name)
            sys.exit(3)
        CURL_HOSTS.append(ip)
        CURL_NAMES.append(name)
if args.https_target:
    for name in args.https_target:
        try:
            ip = socket.gethostbyname(name)
        except:
            stderr("Error resolving name:", name)
            sys.exit(3)
        HTTPS_HOSTS.append('https://' + name)
        HTTPS_NAMES.append(name)

signal.signal(signal.SIGINT, sigint_handler)

stdscr = curses.initscr()
curses.noecho()
stdscr.keypad(1)
stdscr.nodelay(1)
curses.start_color()
curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)

beep = True
worker = 0
if args.action_interval:
    INTERVAL = args.action_interval / 1000.0
print('starting')
for host,name in zip(PING_HOSTS,PING_NAMES):
    print('creating worker ping', host)
    t = WorkerThread(host,name,threading.Lock(),[],True, interval=INTERVAL)
    t.daemon = True
    t.start()
    WORKERS.append(t)
for host,name in zip(CURL_HOSTS, CURL_NAMES):
    print('creating worker curl', host)
    t = WorkerThread(host,name,threading.Lock(),[],False)
    t.daemon = True
    t.start()
    WORKERS.append(t)
for host,name in zip(HTTPS_HOSTS, HTTPS_NAMES):
    print('creating worker curl https', host)
    t = WorkerThread(host,name,threading.Lock(),[],False)
    t.daemon = True
    t.start()
    WORKERS.append(t)
maxWidth = 0
for w in WORKERS:
    width = len("ping " + w.host + " " + w.name + " ")
    if width > maxWidth:
        maxWidth = width

stdscr.move(len(PING_HOSTS) + len(CURL_HOSTS) + 4,0)
stdscr.addstr("Disable bell-limiting in PuTTy to make bells audible.")
stdscr.move(stdscr.getyx()[0]+1,0)
stdscr.addstr("Press 'b' to toggle the bell:")
stdscr.move(stdscr.getyx()[0],30)
stdscr.addstr("[ON] OFF")
stdscr.move(stdscr.getyx()[0]+1,0)
stdscr.addstr("Press 'c' to clear the success and fail counters.")

while True:
    key = stdscr.getch()
    #if 'b' is pressed
    if key == 98:
        stdscr.move(len(PING_HOSTS) + len(CURL_HOSTS) + 5,30)
        if beep:
            beep = False
            stdscr.addstr(" ON [OFF]")
        else:
            beep = True
            stdscr.addstr("[ON] OFF ")
    if key == 99:
        #clear counters
        stdscr.move(2,0)
        for worker in WORKERS:
            worker.success = 0
            worker.fail = 0
            worker.oldfail = 0
            worker.oldsuccess = 0
            stdscr.addstr("                                                     ")
            stdscr.move(stdscr.getyx()[0]+1,0)
    screenInterval = 0.066
    stdscr.addstr(0,0,"Action Interval: %dms  Refresh Interval: %dms" %(INTERVAL*1000, screenInterval*1000))
    stdscr.addstr(1,0,"Action   Host       Name", curses.A_BOLD)
    stdscr.addstr(1,maxWidth-2,"Success|Fail|Code|Last Ten RTTs (ms)", curses.A_BOLD)
    alert = False
    for worker in WORKERS:
        stdscr.move(stdscr.getyx()[0]+1,0)
        temp = addWorkerString(stdscr, worker)
        if temp: alert = True
    if beep and alert:
        curses.beep()
        #curses.flash()
    time.sleep(screenInterval)
    stdscr.refresh()
