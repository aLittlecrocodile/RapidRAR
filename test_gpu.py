#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试GPU加速功能
"""

import os
import time
import argparse
import numpy as np
import pycuda.driver as cuda
import cupy as cp
import traceback
import logging

from src.gpu_manager import GPUManager
from src.config import DEFAULT_CHARSET

def test_gpu_detection():
    """测试GPU检测功能"""
    print("测试GPU检测功能...")
    
    # 初始化CUDA
    cuda.init()
    
    # 获取可用GPU数量
    gpu_count = cuda.Device.count()
    print(f"系统中发现 {gpu_count} 个CUDA设备")
    
    # 显示每个GPU的信息
    for i in range(gpu_count):
        device = cuda.Device(i)
        attrs = device.get_attributes()
        
        print(f"\nGPU {i}: {device.name()}")
        print(f"  计算能力: {device.compute_capability()[0]}.{device.compute_capability()[1]}")
        print(f"  总内存: {device.total_memory() / (1024**3):.2f} GB")
        print(f"  CUDA核心数量: {attrs[cuda.device_attribute.MULTIPROCESSOR_COUNT]}")
        print(f"  时钟频率: {attrs[cuda.device_attribute.CLOCK_RATE] / 1000} MHz")
        print(f"  最大线程/块: {attrs[cuda.device_attribute.MAX_THREADS_PER_BLOCK]}")
        print(f"  最大共享内存/块: {attrs[cuda.device_attribute.MAX_SHARED_MEMORY_PER_BLOCK] / 1024} KB")
    
    return gpu_count

def test_password_generation(gpu_id, batch_size, length):
    print(f"\n在GPU {gpu_id} 上测试密码生成性能...")
    try:
        # 初始化 GPU
        cuda.init()
        device = cuda.Device(gpu_id)
        print(f"使用 GPU: {device.name()}")
        
        # 生成随机密码索引
        indices = np.random.randint(0, len(DEFAULT_CHARSET), size=(batch_size, length), dtype=np.int32)
        
        # CPU 基准测试
        start_time = time.time()
        cpu_passwords = generate_passwords_cpu(indices)
        cpu_time = time.time() - start_time
        cpu_speed = batch_size / cpu_time
        
        # GPU 测试
        with cp.cuda.Device(gpu_id):  # 确保在正确的GPU上执行
            # 将数据传输到GPU
            start_time = time.time()
            gpu_indices = cp.asarray(indices)
            charset_array = cp.array([ord(c) for c in DEFAULT_CHARSET], dtype=cp.int32)
            
            # 生成密码
            gpu_passwords = generate_passwords_gpu(gpu_indices, charset_array)
            cp.cuda.stream.get_current_stream().synchronize()
            gpu_time = time.time() - start_time
            gpu_speed = batch_size / gpu_time
            
            # 将结果转换回字符串
            gpu_results = cp.asnumpy(gpu_passwords)
            gpu_str_passwords = np.array([[chr(c) for c in row] for row in gpu_results[:10]])
        
        # 验证结果
        cpu_results = cpu_passwords[:10]
        match = np.array_equal(cpu_results, gpu_str_passwords)
        
        print(f"\nCPU 速度: {cpu_speed:.2f} 密码/秒")
        print(f"GPU 速度: {gpu_speed:.2f} 密码/秒")
        print(f"加速比: {gpu_speed/cpu_speed:.2f}x")
        print(f"结果验证: {'通过' if match else '失败'}")
        
        if not match:
            print("\n前10个密码比较:")
            print("CPU:", [''.join(p) for p in cpu_results])
            print("GPU:", [''.join(p) for p in gpu_str_passwords])
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        traceback.print_exc()

def generate_passwords_gpu(indices, charset_array):
    """在GPU上生成密码"""
    return charset_array[indices]

def generate_passwords_cpu(indices):
    """在CPU上生成密码"""
    passwords = np.empty((indices.shape[0], indices.shape[1]), dtype='U1')
    for i in range(indices.shape[0]):
        for j in range(indices.shape[1]):
            passwords[i, j] = DEFAULT_CHARSET[indices[i, j]]
    return passwords

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试GPU加速功能')
    parser.add_argument('--gpu', type=int, default=0, help='GPU ID')
    parser.add_argument('--batch_size', type=int, default=1000000, help='批处理大小')
    parser.add_argument('--length', type=int, default=8, help='密码长度')
    
    args = parser.parse_args()
    
    print("GPU加速测试工具")
    print("=" * 60)
    
    try:
        # 测试GPU检测
        gpu_count = test_gpu_detection()
        
        if gpu_count > 0:
            # 确保请求的GPU ID有效
            if args.gpu >= gpu_count:
                print(f"警告: GPU ID {args.gpu} 无效，使用默认GPU 0")
                args.gpu = 0
            
            # 测试密码生成性能
            test_password_generation(args.gpu, args.batch_size, args.length)
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        traceback.print_exc()
    
    print("\n测试完成")

if __name__ == "__main__":
    main() 