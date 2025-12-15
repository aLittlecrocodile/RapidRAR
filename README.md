# RapidRAR DevOps Project

<div align="center">

<!-- Button to launch the web presentation -->
[![Presentation](https://img.shields.io/badge/🚀_Launch_Interactive_Slides-Click_Here-blueviolet?style=for-the-badge&logo=googlechrome)](https://alittlecrocodile.github.io/RapidRAR/)

</div>

## 🚀 Project Overview

This project transforms a CLI tool into a **Cloud-Native Distributed System**.

| Task | Challenge | Key Solution | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Task 1** | Run Python app on any OS (Mac M1/Linux) | **Multi-arch Docker Build** | Docker Buildx, QEMU |
| **Task 2** | Maximize CPU usage on all cluster nodes | **K8s DaemonSet** | Kubernetes, Python API |
| **Task 3** | Test PRs safely without breaking Staging | **Namespace Isolation** | GitHub Actions, Ingress |
| **Bonus** | Security & Cost Management | **App Auth & Auto-Cleanup** | API Key, K8s CronJob |

---

## 🛠 Architecture Highlights

### 1. Ephemeral PR Environments (Task 3)
We solved the "Shared Staging Conflict" by creating dynamic, isolated environments for every Pull Request.

```mermaid
graph LR
    Dev[Developer] -->|Push PR #101| CI[GitHub Actions]
    CI -->|Create| NS[Namespace: pr-101]
    
    subgraph K8s Cluster
        Staging[Namespace: staging]
        NS
    end
    
    User -->|pr-101.example.com| NS
    User -->|staging.example.com| Staging
```

### 2. Distributed Computation (Task 2)
Using **DaemonSet** ensures that RapidRAR scales horizontally to every node in the cluster automatically.

```mermaid
graph TD
    LB[Ingress Load Balancer] --> Svc[Service]
    Svc --> Pod1[Node 1: RapidRAR]
    Svc --> Pod2[Node 2: RapidRAR]
    Svc --> Pod3[Node 3: RapidRAR]
    
    subgraph Cluster Strategy
    Note[DaemonSet ensures 1 Pod per Node]
    end
```

---

## 📂 Deliverables

- **Source Code**: [src/api.py](src/api.py) (FastAPI Wrapper)
- **Deployment**: [k8s/](k8s/) (Kubernetes Manifests)
- **CI/CD**: [.github/workflows/](.github/workflows/) (GitHub Actions)
- **Design Doc**: [DESIGN.md](DESIGN.md) (Detailed Architecture)

## 🏁 How to Run

### Local Docker
```bash
docker run -p 8000:8000 ghcr.io/alittlecrocodile/rapidrar:latest
```

### Kubernetes Deploy
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

### Run Tests
```bash
python test_k8s.py http://localhost:8000 ./sample.rar
```
