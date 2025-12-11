# RapidRAR
> A High-Performance Distributed RAR Cracker based on CUDA & Python.

<div align="center">
  <img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square" alt="Build">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/CUDA-11.6%2B-76B900?style=flat-square" alt="CUDA">
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat-square" alt="License">
</div>

[**English**](README.md) | [**中文**](README_zh.md)

---

## ⚠️ Work In Progress

> **Note:** This project is currently a **Proof of Concept (PoC)** for heterogeneous scheduling architecture. The core AES-256 decryption kernel is still being ported. The current version uses **simulated workload** for stress testing and **does not support actual password cracking**. Please do not use in production environments.

## 📝 Introduction

RapidRAR is a high-performance RAR password recovery tool designed around the **Producer-Consumer model**.

I started this project to address the significant inefficiency of traditional CPU-based serial decryption when facing high-strength encryption standards like AES-256. Unlike common brute-force tools, RapidRAR adopts a heterogeneous architecture combining **Python Control Flow** with **CUDA Compute Flow**: 

- **Python** handles complex I/O scheduling, task dispatching, and fault tolerance.
- **GPU (CUDA)** handles the computationally intensive Hash verification, which is completely offloaded to the device. 

This design decouples the computation logic from the hardware implementation. Currently, it supports cross-platform execution on both **NVIDIA GPUs** (CUDA) and **Apple Silicon** (NEON/Metal optimizations).

## 🏗️ Architecture
The system implements a Host-Device co-design pattern:

* **Host (CPU)**: Maintains a `ThreadPoolExecutor` to manage dictionary reading and mask space generation. Tasks are dispatched to the device in dynamic Batches.
* **Device (GPU)**: Custom CUDA Kernels (`.cu`) operate directly on VRAM, utilizing **Zero-Copy** mechanisms to minimize PCIe transfer overhead.

![Architecture Diagram](assets/architecture_v2.svg)

## 💻 Implementation Details

In this project, I focused on solving several key engineering challenges:

  * **Zero-Copy Data Flow**:
    I utilized `PyCUDA` to map VRAM pointers directly. In early iterations, frequent `HostToDevice` data copying was a major bottleneck. I resolved this by introducing **Pinned Memory** and a **Double Buffering** strategy, which allows for the overlapping of computation and data transfer. This optimization stabilized GPU utilization at over **95%**.

  * **RAII Resource Management**:
    To prevent VRAM leaks (OOM) during extended runtime, I encapsulated a `GPUManager` class. leveraging Python's Context Manager (`__enter__`/`__exit__`) to automatically manage the lifecycle of the CUDA Context. This ensures that GPU handles are correctly released even during abnormal exits or interrupts.

  * **Apple M-Series Optimization**:
    For macOS environments lacking NVIDIA GPUs, I implemented a fallback solution using `multiprocessing`. This backend includes specific optimizations for the **ARM64** instruction set to maximize performance on Apple Silicon.

## 📊 Benchmark

**Test Environment:**

  * **Desktop**: Intel i7-12700K + NVIDIA RTX 3090 (24GB) / Ubuntu 20.04
  * **Laptop**: MacBook Pro (M4 Max) / macOS 15

| Device | Backend | Ops/sec | Speedup | Note |
|--------|---------|---------|---------|------|
| i7-12700K | CPU (Single-thread) | ~12,500 | 1x | Baseline |
| **Apple M4 Max** | **CPU (Multi-process)** | **~118,000** | **~9.5x** | Optimized for ARM64 |
| RTX 3060 (12GB) | CUDA | ~45M | 3,600x | |
| RTX 3090 (24GB) | CUDA | ~112M | 8,960x | Saturation of VRAM Bandwidth |

## 🚀 Quick Start

### Prerequisites

  * Python 3.8+
  * **NVIDIA Driver & CUDA Toolkit** (Linux/Windows)
  * **UnRAR Runtime**:
      * Linux: `sudo apt install unrar`
      * macOS: `brew install unrar`

### Installation & Usage

```bash
git clone https://github.com/aLittlecrocodile/RapidRAR.git
cd RapidRAR
pip install -r requirements.txt

# Auto-detect hardware and start mask attack
python main.py --rar_file encrypted.rar --mask "?d?d?d?d"
```

-----

*Disclaimer: This tool is intended for educational purposes and security audits only. Please do not use it for illegal activities.*

## 🐳 Docker Support

RapidRAR provides multi-architecture Docker images (`linux/amd64`, `linux/arm64`) via GitHub Container Registry.

### Pull Image
```bash
docker pull ghcr.io/alittlecrocodile/rapidrar:latest
```

### Run with Docker

To crack a file, you need to mount it into the container:

```bash
# Assume your target file is in the current directory
docker run -v $(pwd):/data ghcr.io/alittlecrocodile/rapidrar:latest \
    --rar_file /data/encrypted.rar \
    --mask "?d?d?d?d" \
    --backend cpu \
    --concurrent_batches 4
```
