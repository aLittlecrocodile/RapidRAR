# RapidRAR DevOps: 技术实现与架构复盘

本文档旨在记录 RapidRAR DevOps 项目的关键技术决策、架构设计思路以及实施过程中遇到的挑战与解决方案。

## 1. 项目概览与交付物映射

本项目已完成所有核心面试需求：
*   **Task 1 (Docker)**: `src/api.py` (API化), `Dockerfile`, `.github/workflows/docker-build.yml` (多架构构建)。
*   **Task 2 (K8s Base)**: `k8s/` Manifests (DaemonSet, Service, Ingress), `test_k8s.py` (自动化验证)。
*   **Task 3 (PR Preview)**: `DESIGN.md` (设计思路), `.github/workflows/pr-deploy.yml` (动态环境流水线)。

## 2. 核心设计与权衡 (Design & Reasoning)

### 2.1 服务化改造 (Service Wrapper)
**挑战**: 原生 RapidRAR 是 CLI 工具，无法直接响应网络请求进行负载均衡。
**方案**: 引入 `FastAPI` 层 (`src/api.py`)。
**理由**: 相比编写复杂的 Shell 包装脚本，Python 原生 API 更容易处理参数校验、错误返回，且 FastAPI 的异步特性适合高并发网关场景。

### 2.2 Task 2: 为什么选择 DaemonSet？
**需求**: "Deploy RapidRAR on every node".
**决策**: 使用 **DaemonSet** 而非 Deployment。
**理由**: DaemonSet 是 K8s 中用于“节点级守护进程”的原生控制器。它能保证：
1.  **自动扩容**: 新增 Node 节点时自动部署 Pod，无需人工干预。
2.  **资源最大化**: 确保每个计算节点都参与到密码破解任务中，符合分布式计算的初衷。

### 2.3 Task 3: PR 预览环境的设计哲学
**需求**: "Safely test PRs without disrupting other users".
**方案**: **基于 Namespace 的全隔离环境 (Ephemeral Namespaces)**。

| 方案选项 | 描述 | 采用? | 理由 |
| :--- | :--- | :--- | :--- |
| **共享 Namespace** | 不同 PR 使用不同 Service Name 部署在同一 Namespace | ❌ | 资源命名易冲突，清理困难，ConfigMap/Secret 管理混乱。 |
| **基于路由的复用 (Istio)** | 仅部署变更服务，其他流量路由回 Staging | ❌ | 对于单体/小型项目过于复杂，维护成本高。 |
| **独立 Namespace** | 每个 PR 一个 `rapidrar-pr-xxx` Namespace | ✅ | **隔离性最好**。删除 Namespace 即彻底清理。对现有 Staging 零侵入。 |

**实现细节**:
1.  **动态域名**: Ingress 配置规则 `host: pr-<ID>.rapidrar.example.com`，利用泛域名解析实现流量分发。
2.  **生命周期绑定**: GitHub Actions 监听 PR 的 `opened` (创建) 和 `closed` (销毁) 事件，自动化管理环境生灭。

## 3. CI/CD 集成细节 (Wiring into CI)

流水线设计遵循 "Build Once, Deploy Anywhere" 原则：

1.  **构建阶段 (`docker-build.yml`)**:
    *   主分支 (`main`) 推送：构建 `latest` 标签。
    *   PR 分支 (`experiment/*`) 推送：构建 `pr-<ID>` 或分支名标签。
    *   **关键技术点**: 利用 QEMU 实现 `amd64/arm64` 一次性构建并推送到 GHCR。

2.  **部署阶段 (`pr-deploy.yml`)**:
    *   **触发**: 仅在 Pull Request 更新时运行。
    *   **动态替换**: 使用 `sed` 将模板 YAML 中的 `namespace` 和 `image` 替换为当前 PR 的特定值。
    *   **验证关卡**: 部署后立即运行 `test_k8s.py`，只有通过功能测试（模拟上传破解），CI 才会通过。这防止了坏代码被合并进入主分支。

## 4. 遇到的挑战与解决方案 (Troubleshooting)

在实施过程中解决的真实问题：

*   **问题 1: Docker Registry 401 Unauthorized**
    *   **原因**: GitHub Container Registry (GHCR) 对镜像名大小写敏感，且 Workflow 默认 Token 权限不足。
    *   **解决**: 修正镜像名为全小写 (`ghcr.io/owner/repo`)，并显式声明 `packages: write` 权限。
*   **问题 2: CI 未正确触发**
    *   **原因**: Workflow 的 `paths` 过滤器漏掉了 `.github/workflows` 目录，导致仅修改配置文件的 Commit 被忽略。
    *   **解决**: 完善 `paths` 规则，确保基础设施代码变更也能触发验证。

## 5. 假设与未来工作 (Assumptions & Future Work)

**当前假设**:
*   K8s 集群已安装 NGINX Ingress Controller。
*   集群支持动态 LoadBalancer 或已配置好通配符 DNS (`*.rapidrar.example.com`)。

**未来改进**:
1.  **Helm Chart 化**: 将目前的 `sed` 替换方案升级为 Helm Chart，通过 Values 文件管理环境差异。
2.  **资源配额 (Quota)**: 为 PR Namespace 设置 ResourceQuota，防止大量 PR 耗尽集群资源。
3.  **安全性**: API 目前未鉴权，应添加 Sidecar (如 OAuth2 Proxy) 处理认证。

---
*文档生成时间: 2025-12-15*
