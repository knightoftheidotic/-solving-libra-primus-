# Tor Hardening & Self-hosted Runner Guidance

This document explains recommended steps to run Tor safely and use it only
from a self-hosted runner you control. These are guidelines, not a full
security audit. Adapt for your environment and follow the principle of least privilege.

1) Use a dedicated machine or VM
- Run Tor on a dedicated host or VM that is not used for general purpose tasks.
- Keep the host updated and patched.

2) Run Tor as an unprivileged user
- Create a `tor` user and run the Tor daemon under that user. Avoid running Tor as `root`.

3) Use a minimal torrc
- Example safe options to put in `/etc/tor/torrc` or a container's config:

```
Log notice file /var/log/tor/notices.log
RunAsDaemon 1
DataDirectory /var/lib/tor
SocksPort 9050
AvoidDiskWrites 0
# Reduce exposed services
DisableNetwork 0
ClientOnly 1
```

4) Systemd unit (example)
- Create `/etc/systemd/system/tor.service` that starts Tor as the `tor` user and restricts capabilities.

5) Docker example (useful for testing)
- A sample `docker/tor/docker-compose.yml` is provided in this repo. It builds a small Debian-based container that runs Tor and exposes a SOCKS5 proxy on port 9050. Use it only on machines you control.

6) Network policies and firewall
- Restrict outgoing traffic if needed. If you only need to route traffic to the Tor network, allow Tor's necessary ports.

7) Monitoring and logging
- Keep logs from Tor and from your solver. Rotate and protect logs.

8) CI considerations
- Never run Tor on public shared CI. This repo's workflow only starts Tor on jobs that run on `[self-hosted, linux]` and only when you explicitly set the `use_tor` input.

9) Legal & policy
- Confirm that interacting with target endpoints is permitted. Keep explicit authorization records.
