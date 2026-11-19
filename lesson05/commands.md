# Lesson 4 homework - Kubernetes storage, ConfigMap, CronJob, probes

Cluster: Docker Desktop Kubernetes v1.36.1 (kind mode, node `desktop-worker`).
All namespaced resources live in namespace `homework4`.

## Files

| File | Content |
|---|---|
| `01-storage.yaml` | PV `hw4-pv` (2Gi, hostPath `/mnt/hw4-data`) + PVC `hw4-pvc` (1Gi) |
| `02-configmap.yaml` | ConfigMap `nginx-env` (env vars) + ConfigMap `nginx-conf` (`default.conf` with `/healthz`) |
| `03-cronjob.yaml` | PV/PVC for logs + CronJob `date-logger` with a native sidecar |
| `04-service.yaml` | ClusterIP Service `nginx-svc` |
| `nginx-deployment.yaml` | Final Nginx Deployment: PVC + ConfigMaps + readiness + liveness |

## Setup

```bash
kubectl create namespace homework4
kubectl config set-context --current --namespace=homework4
```

## Task 1 - PV and PVC

```bash
kubectl apply -f 01-storage.yaml
kubectl apply -f nginx-deployment.yaml
kubectl get pv,pvc,pods
kubectl exec deploy/nginx -- sh -c 'echo "Hello from PV - Yura homework 4" > /usr/share/nginx/html/index.html'
kubectl exec deploy/nginx -- cat /usr/share/nginx/html/index.html
kubectl delete pod -l app=nginx          # Deployment creates a new pod
kubectl get pods
kubectl exec deploy/nginx -- cat /usr/share/nginx/html/index.html   # file is still there
```

Notes:
- `storageClassName: manual` on both PV and PVC disables dynamic provisioning
  (the default class `standard` would create its own volume otherwise).
- The PVC shows 2Gi capacity: a PVC always gets the whole PV it binds to.

## Task 2 - ConfigMap

```bash
kubectl apply -f 02-configmap.yaml
kubectl describe configmap nginx-env nginx-conf
kubectl apply -f nginx-deployment.yaml
kubectl rollout status deploy/nginx
kubectl exec deploy/nginx -- env | grep APP
kubectl exec deploy/nginx -- cat /etc/nginx/conf.d/default.conf
kubectl exec deploy/nginx -- wget -qO- http://127.0.0.1/healthz   # ok
kubectl exec deploy/nginx -- wget -qO- http://127.0.0.1/          # page from the PV
```

Notes:
- `envFrom.configMapRef` loads every key as an env var; the `nginx-conf` ConfigMap is
  mounted into `/etc/nginx/conf.d` and replaces the image's default config.
- Two ConfigMaps, because `default.conf` is not a valid env var name.
- `localhost` resolves to IPv6 `::1` in the image, but the config listens on IPv4 only,
  so the checks use `127.0.0.1`. Probes use the pod IPv4 address and are not affected.

## Task 3 - CronJob with a sidecar

```bash
kubectl apply -f 03-cronjob.yaml
kubectl get cronjob,jobs,pods
kubectl debug node/desktop-worker --image=busybox:1.37 -- cat /host/mnt/hw4-logs/cron.log
kubectl logs node-debugger-desktop-worker-<id>
kubectl delete pod node-debugger-desktop-worker-<id>
```

Notes:
- Every minute the main container `date-writer` appends the date to a shared `emptyDir`;
  the sidecar `log-shipper` follows it with `tail -F` and appends to `cron.log` on a PV.
- The sidecar is a native sidecar (`initContainers` + `restartPolicy: Always`), so the Job
  can complete: Kubernetes stops it after the main container exits.
- First version: every Job took ~37s. `sh` runs as PID 1 and ignores SIGTERM, so Kubernetes
  waited the 30s grace period before SIGKILL. Fixed with `trap 'exit 0' TERM` + `tail ... &`
  + `wait`; Jobs now take ~6s.
- `successfulJobsHistoryLimit: 3` / `failedJobsHistoryLimit: 1` clean up old Jobs.

## Task 4 - Liveness probe

```bash
kubectl apply -f nginx-deployment.yaml
kubectl describe pod -l app=nginx | grep -i liveness
kubectl exec deploy/nginx -- sh -c 'pkill -STOP -f "worker process"'   # freeze nginx
kubectl get pods -l app=nginx -w                                        # RESTARTS 0 -> 1
kubectl describe pod -l app=nginx | tail -n 12
```

Notes:
- HTTP GET `/healthz` on port 80 every 5s, timeout 2s, restart after 3 failures.
- Freezing the worker processes with SIGSTOP simulates a hung app (not a crash), so the
  restart is caused by the probe: events show `Liveness probe failed: ... context deadline
  exceeded` and `Container nginx failed liveness probe, will be restarted`.

## Task 5 - Readiness probe

```bash
kubectl apply -f 04-service.yaml
kubectl apply -f nginx-deployment.yaml
kubectl get pods -l app=nginx -w
kubectl describe pod -l app=nginx | tail -n 10
kubectl get endpointslices -l kubernetes.io/service-name=nginx-svc
```

Notes:
- `tcpSocket` probe on port 80. The container sleeps 30s before starting nginx
  to simulate a slow startup.
- During the delay the new pod is `Running 0/1` and is not in the Service endpoints;
  events show `Readiness probe failed: ... connection refused` and no restart.
- The rolling update kept the old pod serving traffic until the new one became `1/1`,
  then terminated it: zero downtime.
- Liveness `initialDelaySeconds` was raised from 5 to 40, otherwise it would kill the
  container during the 30s startup (CrashLoopBackOff). In production a `startupProbe`
  is the proper tool for this.

## Cleanup

```bash
kubectl delete namespace homework4
kubectl delete pv hw4-pv hw4-logs-pv
kubectl config set-context --current --namespace=default
```
