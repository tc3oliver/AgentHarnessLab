`/app/sample.log` is a web access log. Write `/app/loganalyze.py`, run as `python3 /app/loganalyze.py LOGFILE`.
It prints one JSON object to stdout with:
- `"total_requests"`: the number of well-formed lines (see the sample for the format);
- `"top_5xx_ips"`: up to three `[ip, count]` pairs for the client IPs with the most responses whose status
  is 500-599, sorted by count descending and then IP ascending (plain string order).

A well-formed line is: client IP, two more space-separated fields, a `[bracketed time]`, a quoted request
(`"METHOD PATH PROTOCOL"`), a three-digit status, a response size (digits or `-`) and a response time.
Lines that do not match this (blank, truncated, garbage) are skipped and are not counted. Empty input gives
`{"total_requests": 0, "top_5xx_ips": []}`.
