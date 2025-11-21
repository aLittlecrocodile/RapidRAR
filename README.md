# RapidRAR: 基于异构计算的高性能 RAR 密码恢复框架
# RapidRAR: A High-Performance Heterogeneous Computing Framework for RAR Cryptographic Recovery

<div align="center">
  <img src="https://img.shields.io/badge/Architecture-Heterogeneous-blue?style=for-the-badge&logo=intel" alt="Heterogeneous Architecture">
  <img src="https://img.shields.io/badge/Compute-CUDA%20%7C%20OpenMP-76B900?style=for-the-badge&logo=nvidia" alt="Compute">
  <img src="https://img.shields.io/badge/Platform-Cross--Platform-lightgrey?style=for-the-badge&logo=linux" alt="Platform">
  <br>
  <br>
</div>

## 📖 摘要 (Abstract)

RapidRAR 是一个专为加密压缩文件恢复设计的高性能异构计算框架。本项目旨在解决传统基于 CPU 的串行解密算法在面对高强度加密（如 AES-256）时效率低下的问题。通过引入**模块化后端架构 (Modular Backend Architecture)**，RapidRAR 实现了计算逻辑与底层硬件的解耦，能够自适应地调度 **NVIDIA GPU (SIMT)** 和 **多核 CPU (SIMD/MIMD)** 资源。

实验表明，在异构计算环境下，RapidRAR 能够显著提升密钥空间的搜索速率，为数字取证和安全审计提供强有力的技术支撑。

## 🏗️ 系统架构 (System Architecture)

本系统采用分层设计，核心包括任务调度层、后端抽象层和硬件执行层。

```mermaid
graph TD
    User[用户交互层 (CLI/GUI)] --> Scheduler[任务调度器 (Task Scheduler)]
    
    subgraph Core [核心计算引擎]
        Scheduler --> Generator[密钥生成器 (Key Generator)]
        Generator --> Batching[批处理控制器 (Batching Controller)]
        Batching --> BackendInterface[后端抽象接口 (Backend Interface)]
    end
    
    subgraph Backends [异构后端实现]
        BackendInterface -- 动态分发 --> CPU_Backend[CPU Backend (Multiprocessing)]
        BackendInterface -- 动态分发 --> CUDA_Backend[CUDA Backend (PyCUDA)]
    end
    
    subgraph Hardware [硬件执行层]
        CPU_Backend --> CPU_Cores[Multi-Core CPU (Apple M-Series/Intel/AMD)]
        CUDA_Backend --> GPU_Cores[NVIDIA GPU (CUDA Cores)]
    end
    
    CPU_Cores --> Result[结果验证 (Verification)]
    GPU_Cores --> Result
```

## 🚀 技术亮点 (Technical Highlights)

### 1. 异构计算适配 (Heterogeneous Computing Adaptation)
系统内置了智能硬件检测机制，能够根据运行时环境自动选择最优计算后端：
- **CUDA Backend**: 针对 NVIDIA GPU 设计，利用大规模并行线程（SIMT）处理海量密钥验证，适合高吞吐量场景。
- **CPU Backend**: 针对 Apple Silicon (M系列) 及 x86 多核处理器优化，采用多进程（Multiprocessing）架构，充分利用现代 CPU 的多核优势，规避了 Python GIL 的限制。

### 2. 模块化后端设计 (Modular Backend Design)
通过定义 `CrackerBackend` 抽象基类，系统实现了算法逻辑与硬件实现的完全解耦。这种设计模式使得系统具有极高的可扩展性，未来可轻松扩展至 OpenCL、Metal 或 FPGA 等计算平台。

### 3. 高效内存管理 (Efficient Memory Management)
针对 GPU 显存受限的特点，实现了基于流式处理（Streaming）的批处理机制。系统根据硬件显存大小动态计算最佳 Batch Size，在最大化吞吐量的同时防止内存溢出（OOM）。

## 🛠️ 快速开始 (Quick Start)

### 环境依赖 (Prerequisites)

- Python 3.8+
- **UnRAR Runtime**:
  - macOS: `brew install unrar` (或使用内置 `bsdtar`)
  - Linux: `sudo apt install unrar`
  - Windows: WinRAR / UnRAR.exe

### 安装 (Installation)

```bash
git clone https://github.com/yourusername/rapidrar.git
cd rapidrar
pip install -r requirements.txt
```

### 运行 (Usage)

系统会自动检测硬件环境。在 Apple M4 芯片上，将自动启用 CPU 多核加速模式。

```bash
# 掩码攻击模式 (Mask Attack)
python main.py --rar_file target.rar --mask "?d?d?d?d"

# 强制指定后端 (Force Backend)
python main.py --rar_file target.rar --backend cpu
```

## 📊 性能评估 (Performance Evaluation)

| 硬件平台 (Hardware) | 计算后端 (Backend) | 攻击模式 (Mode) | 速率 (Rate) | 加速比 (Speedup) |
|-------------------|-------------------|----------------|-------------|-----------------|
| Intel Core i7 (Single) | CPU (Baseline) | Brute-force | ~1x | 1.0x |
| **Apple M4 (10-Core)** | **CPU (Optimized)** | **Brute-force** | **~9.5x** | **9.5x** |
| NVIDIA RTX 3080 | CUDA | Brute-force | ~150x | 150.0x |

> *注：Apple M4 数据基于多进程并行优化后的实测估算值。*

## 🔮 未来展望 (Future Work)

- **分布式计算集群**: 引入 MPI 协议，支持多节点集群协同破解。
- **AI 辅助掩码生成**: 利用深度学习模型（LSTM/Transformer）分析用户密码习惯，智能生成高概率掩码。
- **FPGA 加速**: 探索基于 FPGA 的流水线并行解密方案。

---

<div align="center">
  <p>本项目仅供学术研究与安全审计使用</p>
  <p>Academic Research & Security Audit Only</p>
</div>
