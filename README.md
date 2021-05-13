# ping-script
Python3/curses CLI tool to ping/curl multiple hosts and monitor for service interruptions.

Sample CLI:
```sh
me@home:ping-script$ ./ping_script.py google.com 1.1.1.1 2.2.2.2

Action Interval: 500ms  Refresh Interval: 66ms
Action   Host       Name     Success|Fail|Code|Last Ten RTTs (ms)
ping 172.217.13.238 google.com 25    0    OK   6.4  6.4  6.3  6.3  6.4  6.4  6.4  6.4  6.4  6.2
ping 1.1.1.1 1.1.1.1           25    0    OK   6.1  6.0  6.0  6.0  6.0  6.1  6.0  6.0  6.1  6.0
ping 2.2.2.2 2.2.2.2           0     24   FAIL .    .    .    .    .    .    .    .    .    .


Disable bell-limiting in PuTTy to make bells audible.
Press 'b' to toggle the bell: [ON] OFF
Press 'c' to clear the success and fail counters.
```

Most of the code is from 2013. Small improvements over the years.
