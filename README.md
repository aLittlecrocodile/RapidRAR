# RapidRAR
> A High-Performance Distributed RAR Cracker based on CUDA & Python.

<div align="center">
  <img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square" alt="Build">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/CUDA-11.6%2B-76B900?style=flat-square" alt="CUDA">
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat-square" alt="License">
</div>

[**English**](README.md) | [**中文**](README_zh.md)

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

![Architecture Diagram](https://mermaid.ink/img/Zmxvd2NoYXJ0IExSCiAgICAlJSDmlbTkvZPmqKrlkJHluIPlsYDvvIzlg4_kuIDmnaHmtYHmsLTnur8KICAgIAogICAgJSUg5a6a5LmJ5LiA5Lqb566A5Y2V55qE5qC35byP77yM5LiN6KaB5aSq6Iqx5ZOoCiAgICBjbGFzc0RlZiBwbGFpbiBmaWxsOiNmZmYsc3Ryb2tlOiMzMzMsc3Ryb2tlLXdpZHRoOjFweDsKICAgIGNsYXNzRGVmIGRiIGZpbGw6I2VlZSxzdHJva2U6IzMzMyxzdHJva2Utd2lkdGg6MXB4LHN0cm9rZS1kYXNoYXJyYXk6IDUgNTsKICAgIAogICAgc3RhcnQoKFN0YXJ0KSkgLS0-IGlucHV0W0NMSSAvIEFyZ3VtZW50c10KICAgIGlucHV0IC0tPiBpbml0W0dQVSBNYW5hZ2VyIEluaXRdCiAgICAKICAgICUlIFB5dGhvbiDmjqfliLblsYIgLSDkvZzkuLrkuIDkuKrmlbTkvZMKICAgIHN1YmdyYXBoIEhvc3QgW_CfkI0gSG9zdCBDb250ZXh0IChQeXRob24pXQogICAgICAgIGRpcmVjdGlvbiBUQgogICAgICAgIGluaXQgLS0-IGJhdGNoZXJbQmF0Y2ggR2VuZXJhdG9yXQogICAgICAgIGJhdGNoZXIgLS0-fDEuIFRhc2sgUXVldWV8IHRocmVhZFtUaHJlYWRQb29sXQogICAgZW5kCgogICAgJSUg5pWw5o2u5Lyg6L6TIC0g6YeN54K55qCH5Ye6IFBDSWUKICAgIHRocmVhZCA9PSAiUENJZSBCdXMgKEgyRCkiID09PiB2cmFtX2luCiAgICAKICAgICUlIEdQVSDorqHnrpflsYIKICAgIHN1YmdyYXBoIERldmljZSBb4pqhIERldmljZSBDb250ZXh0IChDVURBKV0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICB2cmFtX2luWyhWUkFNIElucHV0KV0gLS0-IGtlcm5lbFtDVURBIEtlcm5lbAooUGFyYWxsZWwgSGFzaCldCiAgICAgICAga2VybmVsIC0tPiB2cmFtX291dFsoUmVzdWx0IEJpdG1hcCldCiAgICBlbmQKICAgIAogICAgJSUg57uT5p6c5Zue5LygCiAgICB2cmFtX291dCA9PSAiUENJZSBCdXMgKEQySCkiID09PiBmaWx0ZXIKICAgIAogICAgJSUg6aqM6K-B5bGCCiAgICBzdWJncmFwaCBWZXJpZnkgW1ZhbGlkYXRpb25dCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgZmlsdGVye0NhbmRpZGF0ZT99CiAgICAgICAgY2hlY2tbVW5SQVIgLyBDUFUgVmVyaWZ5XQogICAgZW5kCiAgICAKICAgIGZpbHRlciAtLSBZZXMgLS0-IGNoZWNrCiAgICBmaWx0ZXIgLS0gTm8gLS0-IGJhdGNoZXIKICAgIAogICAgY2hlY2sgLS0gUGFzcyAtLT4gZm91bmQoKOKchSBQYXNzd29yZCBGb3VuZCkpCiAgICBjaGVjayAtLi0-fEZhbHNlIFBvc2l0aXZlfCBiYXRjaGVyCgogICAgJSUg5bqU55So5qC35byPCiAgICBjbGFzcyBpbnB1dCxpbml0LGJhdGNoZXIsdGhyZWFkLGtlcm5lbCxjaGVjayxmaWx0ZXIgcGxhaW47CiAgICBjbGFzcyB2cmFtX2luLHZyYW1fb3V0IGRiOw==)

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
