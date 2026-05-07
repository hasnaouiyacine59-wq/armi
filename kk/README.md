# Docker + NordVPN Container Notes

## Problem
Running VPN inside a container with `--network host` changes the host machine's IP.

## Fix: Remove `--network host`

```bash
docker run -d \
  --name n-1 \
  --privileged \
  --device /dev/net/tun \
  -e NORDVPN_TOKEN="your_token" \
  -e NORDVPN_ANALYTICS=false \
  quay.io/mylastres0rt05_redhat/lab-bollet:latest
```

Without `--network host`, the container gets its own isolated network namespace — VPN runs inside it, host IP stays untouched.

---

## Run Python Script Inside Container (redirect output to docker logs)

```bash
docker exec n-1 sh -c "python3 /dock_hop/cum.py >> /proc/1/fd/1 2>&1"
```

Read output:

```bash
docker logs n-1
```

`/proc/1/fd/1` is PID 1's stdout, which is what `docker logs` captures.

---

## NordVPN Analytics Prompt (non-interactive fix)

If NordVPN loops asking `Do you allow us to collect and use limited app performance data? (y/n)`, pass the answer via env var or pipe:

```bash
-e NORDVPN_ANALYTICS=false
```

Or pipe answer:

```bash
docker exec n-1 sh -c "echo 'n' | nordvpn login --token your_token >> /proc/1/fd/1 2>&1"
```

---

## Clone a Running Container (with all modifications)

```bash
docker commit n-1 my-n1-snapshot

docker run -d \
  --name n-1-clone \
  --privileged \
  --device /dev/net/tun \
  -e NORDVPN_TOKEN="your_token" \
  my-n1-snapshot
```

`docker commit` captures the full filesystem state including all changes made inside the container.

---

## Push Snapshot to quay.io

```bash
docker commit n-1 my-n1-snapshot
docker tag my-n1-snapshot quay.io/your_username/my-n1-snapshot:latest
docker push quay.io/your_username/my-n1-snapshot:latest
```

Pull and run on any machine:

```bash
docker run -d \
  --name n-1 \
  --privileged \
  --device /dev/net/tun \
  -e NORDVPN_TOKEN="your_token" \
  quay.io/your_username/my-n1-snapshot:latest
```

> **Note:** Runtime state (running processes, RAM, open connections) is NOT saved — only the filesystem. VPN will reconnect on start via the entrypoint, not resume a previous connection.
