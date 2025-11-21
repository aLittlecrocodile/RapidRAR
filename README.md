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

```mermaid
graph TD
    %% Styles
    classDef cpu fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef gpu fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;

    subgraph CPU_Host [🖥️ CPU Host]
        Start((Start)) --> ArgParse[Arg Parse & Env Check]
        ArgParse --> GPU_Init[GPUManager: Init Context]
        GPU_Init --> Attack_Select{Mode Selection}
        
        Attack_Select -- Mask/Brute-force --> Batch_Gen[Task Dispatch: Calculate Search Space]
        Attack_Select -- Dictionary --> Dict_Load[Load Dict & Chunking]
        
        Batch_Gen --> ThreadPool[ThreadPool: Assign Workers]
        Dict_Load --> ThreadPool
        
        subgraph Worker_Thread [Worker Thread]
            Mem_Alloc[Alloc VRAM]
            Data_Copy_H2D[Copy: Host -> Device]
            Kernel_Launch[Launch CUDA Kernel]
            Data_Copy_D2H[Copy: Device -> Host]
            
            Mem_Alloc -.-> Data_Copy_H2D
            Data_Copy_H2D -.-> Kernel_Launch
        end
        
        ThreadPool --> Worker_Thread
        
        Data_Copy_D2H --> Result_Filter{Candidate Found?}
        Result_Filter -- Yes --> CPU_Verify[CPU Final Verify (UnRAR)]
        Result_Filter -- No --> Checkpoint[Update Checkpoint]
        
        CPU_Verify -- Pass --> Success((✅ Success))
        CPU_Verify -- Fail --> Checkpoint
        Checkpoint --> Next_Batch[Next Batch]
        Next_Batch --> ThreadPool
    end

    subgraph GPU_Device [⚡ GPU Device]
        Kernel_Exec[Execute CUDA Kernel]
        
        subgraph Parallel_Compute [Massive Parallelism]
            Thread1[Thread: Gen Password]
            Thread2[Thread: Calc Hash]
            Thread3[Thread: Verify Header]
        end
        
        Kernel_Launch -.-> Kernel_Exec
        Kernel_Exec --> Parallel_Compute
        Parallel_Compute --> Result_Bitmap[Result Bitmap]
        Result_Bitmap -.-> Data_Copy_D2H
    end

    class Start,ArgParse,GPU_Init,Attack_Select,Batch_Gen,Dict_Load,ThreadPool,Worker_Thread,Result_Filter,CPU_Verify,Checkpoint,Next_Batch cpu;
    class Kernel_Exec,Parallel_Compute,Thread1,Thread2,Thread3,Result_Bitmap,Mem_Alloc,Data_Copy_H2D,Data_Copy_D2H gpu;
```

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
