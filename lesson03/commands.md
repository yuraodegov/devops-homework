# Lesson 3 Homework - Kubernetes (Superset, Airflow, Postgres)

Environment: Docker Desktop Kubernetes (kind provisioning, node `desktop-worker`), namespace `homework3`.

## Setup

```bash
kubectl create namespace homework3
kubectl config set-context --current --namespace=homework3
```

## 1-2. Deploy Superset with kubectl, check and describe the pod

```bash
kubectl run superset --image=amancevice/superset --port=8088
kubectl get pods -w
kubectl describe pod superset
```

## 3. Create a Service and expose it outside the cluster

```bash
kubectl expose pod superset --type=NodePort --port=8088 --name=superset-svc
kubectl get svc
kubectl get endpointslices
```

Note: the cluster runs in **kind** mode, where each node is a Docker container.
NodePort `32651` is open on the node but is not published to `localhost` of the host,
so `curl localhost:32651` fails. Access from the host was done with port-forward:

```bash
kubectl port-forward svc/superset-svc 8088:8088
# http://localhost:8088
```

## 4. Delete both resources

```bash
kubectl delete svc superset-svc
kubectl delete pod superset
kubectl get all
```

## 5-6. Same via YAML (`apps.yaml`)

```bash
kubectl apply -f apps.yaml
kubectl get pods,svc -o wide
kubectl get endpointslices
kubectl describe pod superset
```

## 7. Add Airflow (pod + NodePort service) to the same YAML

```bash
kubectl apply -f apps.yaml      # superset unchanged, airflow created
kubectl get pods,svc -o wide
kubectl get endpointslices
```

## 8. Resources and environment variables

Requests: `cpu: 250m`, `memory: 250Mi`. Limits: `cpu: 500m`, `memory: 500Mi`.
Env: `APPLICATION=superset` / `APPLICATION=airflow`.

Pods are immutable (env/resources cannot be changed on a running pod), so they were recreated:

```bash
kubectl delete -f apps.yaml
kubectl apply -f apps.yaml
kubectl get pods -w
kubectl describe pod superset | grep -A 6 -E "Limits|Environment"
kubectl describe pod airflow  | grep -A 6 -E "Limits|Environment"
kubectl describe pod superset | grep QoS                 # Burstable (was BestEffort)
kubectl describe pod superset | grep -A 5 "Last State"   # Reason: OOMKilled, Exit Code: 137
```

**Finding:** with a 500Mi memory limit both applications are killed by the kernel
(`OOMKilled`, exit code 137 = SIGKILL) and go into `CrashLoopBackOff`.
Superset and Airflow need more than 500Mi to start (Python + gunicorn workers).

## 9. Connect into a pod and check the variable

```bash
kubectl exec airflow -- printenv APPLICATION     # -> airflow
kubectl exec -it airflow -- bash                 # echo $APPLICATION
```

## Bonus (`apps-bonus.yaml`)

Memory limits raised so the apps run stably: Superset `3Gi` (web server + init commands),
Airflow `1536Mi`. Added `SUPERSET_SECRET_KEY` (Superset >= 2.1 refuses to start with the default key)
and a Postgres pod with a ClusterIP service.

```bash
kubectl delete -f apps.yaml
kubectl apply -f apps-bonus.yaml
kubectl get pods -w                      # all Running, RESTARTS 0

# Superset initialisation
kubectl exec superset -- superset db upgrade
kubectl exec superset -- superset fab create-admin --username admin --firstname Yura --lastname Odegov --email admin@example.com --password admin
kubectl exec superset -- superset init

# Open both apps in the browser
kubectl port-forward svc/superset-svc 8088:8088 > /dev/null 2>&1 &   # http://localhost:8088
kubectl port-forward svc/airflow-svc 8080:8080 > /dev/null 2>&1 &    # http://localhost:8080

# Postgres check
kubectl exec -it postgres -- psql -U demo -d demodb
#   \l
#   SELECT version();
```

### What each application offers

- **Apache Superset** - open-source BI / data-visualization platform: connects to SQL databases,
  SQL Lab editor, charts and interactive dashboards.
- **Apache Airflow** - workflow orchestrator: pipelines are written in Python as DAGs
  (tasks + dependencies) and run on a schedule, with a web UI for monitoring and retries.
- **PostgreSQL** - open-source relational database (SQL, transactions, indexes).
  Commonly used as the metadata database for both Superset and Airflow.
