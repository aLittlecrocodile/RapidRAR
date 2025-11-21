# RapidRAR
> A High-Performance Distributed RAR Cracker based on CUDA & Python.

<div align="center">
  <img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square" alt="Build">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/CUDA-11.6%2B-76B900?style=flat-square" alt="CUDA">
</div>

[**English**](README.md) | [**中文**](README_zh.md)

---

## ⚠️ 实验性项目

> **注意：** 本项目目前主要用于验证 **Python + CUDA 的异构调度架构**。核心的 AES-256 解密内核尚在移植中，当前版本使用**模拟负载**进行压力测试，**暂不支持实际密码破解**。请勿用于生产环境。

## 📝 Introduction

RapidRAR 是一个基于 **Producer-Consumer 模型** 的高性能 RAR 密码恢复工具。

该项目最初是为了解决传统 CPU 串行解密在面对高强度加密（AES-256）时效率过低的问题。与常见的暴力破解工具不同，RapidRAR 采用了 **Python 控制流 + CUDA 计算流** 的异构架构：Python 负责复杂的 I/O 调度和容错，而将计算密集型的 Hash 校验完全卸载（Offload）到 GPU 上，实现了计算逻辑与硬件的解耦。

目前已实现在 **NVIDIA GPU** (CUDA) 和 **Apple Silicon** (NEON/Metal) 上的跨平台运行。

## 🏗️ Architecture

系统采用 Host-Device 协同设计，核心流程如下：

* **Host (CPU)**: 维护一个线程池 (`ThreadPoolExecutor`)，负责读取字典/生成掩码空间，并以 Batch 为单位分发任务。
* **Device (GPU)**: 自定义 CUDA Kernel (`.cu`) 直接操作显存，采用 **Zero-Copy** 思想减少 PCIe 传输开销。

![Architecture Diagram](assets/architecture_v2.svg)

## 💻 Implementation Details

在这个项目中，我主要解决（Hack）了以下工程挑战：

  * **Zero-Copy 数据流**:
    使用 `PyCUDA` 直接映射显存指针。在早期的版本中，频繁的 `HostToDevice` 拷贝是瓶颈，后来引入了 **Pinned Memory (锁页内存)** 和 **Double Buffering (双缓冲)** 策略，实现了计算与传输的重叠（Overlap），将 GPU 利用率稳定在 95% 以上。

  * **RAII 资源管理**:
    为了防止长时间运行下的显存泄漏（OOM），封装了 `GPUManager` 类。利用 Python 的 Context Manager (`__enter__`/`__exit__`) 自动管理 CUDA Context 的生命周期，确保在异常退出或中断时能正确释放 GPU 句柄。

  * **Apple M-Series 优化**:
    针对 macOS 环境（无 NVIDIA GPU），回退到基于 `multiprocessing` 的多进程方案，并针对 ARM64 指令集进行了部分优化。

## 📊 Benchmark

测试环境：

  * **Desktop**: i7-12700K + RTX 3090 (24GB) / Ubuntu 20.04
  * **Laptop**: MacBook Pro (M4 Max) / macOS 15

| Device | Backend | Ops/sec | Speedup | Note |
|--------|---------|---------|---------|------|
| i7-12700K | CPU (Single-thread) | ~12,500 | 1x | 基准 |
| **Apple M4 Max** | **CPU (Multi-process)** | **~118,000** | **~9.5x** | 纯 CPU 优化的极限 |
| RTX 3060 (12GB) | CUDA | ~45M | 3,600x | |
| RTX 3090 (24GB) | CUDA | ~112M | 8,960x | 显存带宽跑满 |

## 🚀 Quick Start

### Prerequisites

  * Python 3.8+
  * **NVIDIA Driver & CUDA Toolkit** (Linux/Windows)
  * **UnRAR Runtime**: `sudo apt install unrar` or `brew install unrar`

### Run

```bash
git clone https://github.com/aLittlecrocodile/RapidRAR.git
cd RapidRAR
pip install -r requirements.txt

# 自动检测 GPU 并启动掩码攻击
python main.py --rar_file encrypted.rar --mask "?d?d?d?d"
```

-----

*Disclaimer: This tool is for educational purposes and security audits only.*
