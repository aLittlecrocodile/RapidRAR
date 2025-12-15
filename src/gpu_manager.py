#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GPU资源管理器
"""

import os
import time
import logging
import numpy as np
try:
    import pycuda.driver as cuda
    from pycuda.compiler import SourceModule
    HAS_PYCUDA = True
except ImportError:
    HAS_PYCUDA = False
    # Mock cuda for type hinting or safe failure
    class MockCuda:
        class Error(Exception): pass
        class device_attribute:
            MULTIPROCESSOR_COUNT = 0
            MAX_THREADS_PER_BLOCK = 0
            CLOCK_RATE = 0
            MAX_GRID_DIM_X = 0
    cuda = MockCuda()
    SourceModule = None
import psutil

try:
    from src.cuda_kernels import get_kernel_code
except ImportError:
    def get_kernel_code():
        raise RuntimeError("CUDA kernels not available")

from src.config import DEFAULT_THREADS_PER_BLOCK, DEFAULT_MAX_BLOCKS

logger = logging.getLogger(__name__)

class GPUManager:
    """
    GPU资源管理类，负责CUDA环境初始化、内存分配和多GPU协调
    """
    def __init__(self, gpu_ids):
        """
        初始化GPU管理器
        
        Args:
            gpu_ids (list): GPU设备ID列表
        """
        self.gpu_ids = gpu_ids
        self.contexts = []
        self.devices = []
        
        try:
            cuda.init()
        except cuda.Error:
            pass  # 已经初始化则忽略
        
        # 验证GPU
        device_count = cuda.Device.count()
        if device_count == 0:
            raise RuntimeError("未检测到CUDA设备")
            
        for gpu_id in gpu_ids:
            if gpu_id >= device_count:
                raise ValueError(f"无效的GPU ID: {gpu_id}")
            self.devices.append(cuda.Device(gpu_id))
        
        logging.info(f"已初始化 {len(self.devices)} 个GPU设备")

    def __enter__(self):
        """上下文管理器入口"""
        for device in self.devices:
            try:
                context = device.make_context()
                self.contexts.append(context)
                context.pop()
            except cuda.Error as e:
                logging.error(f"创建CUDA上下文失败: {e}")
                self.cleanup()
                raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()
        return False

    def cleanup(self):
        """清理CUDA资源"""
        while self.contexts:
            try:
                context = self.contexts.pop()
                context.pop()
                context.detach()
            except:
                pass

    def get_device(self, idx=0):
        """获取指定索引的GPU设备"""
        if idx >= len(self.devices):
            raise ValueError(f"GPU索引 {idx} 超出范围")
        return self.devices[idx]

    def push_context(self, idx=0):
        """推入指定GPU设备的上下文"""
        if idx >= len(self.contexts):
            raise ValueError(f"GPU索引 {idx} 超出范围")
        self.contexts[idx].push()
        return self.contexts[idx]
        
    def pop_context(self, idx=0):
        """弹出指定GPU设备的上下文"""
        if idx >= len(self.contexts):
            raise ValueError(f"GPU索引 {idx} 超出范围")
        return self.contexts[idx].pop()

    def _compile_kernels(self, gpu_id):
        """
        编译CUDA核函数
        
        Args:
            gpu_id: GPU ID
        """
        # 获取CUDA核函数代码
        kernel_codes = get_kernel_code()
        
        # 为这个GPU编译所有核函数
        self.functions[gpu_id] = {}
        
        # 激活此GPU的上下文
        self.contexts[gpu_id].push()
        
        try:
            # 编译RAR密码检查核函数
            module = SourceModule(kernel_codes['rar_check'])
            self.functions[gpu_id]['check_rar_password'] = module.get_function("check_rar_password")
            
            # 编译掩码生成核函数
            module = SourceModule(kernel_codes['mask_generate'])
            self.functions[gpu_id]['generate_mask_passwords'] = module.get_function("generate_mask_passwords")
            
            # 编译字典攻击核函数
            module = SourceModule(kernel_codes['dict_check'])
            self.functions[gpu_id]['check_dictionary_passwords'] = module.get_function("check_dictionary_passwords")
            
            # 编译年份组合核函数
            module = SourceModule(kernel_codes['year_combine'])
            self.functions[gpu_id]['combine_with_years'] = module.get_function("combine_with_years")
        finally:
            # 弹出上下文
            cuda.Context.pop()
    
    def get_memory_info(self, gpu_id):
        """
        获取指定GPU的内存信息
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            总内存和空闲内存元组 (total, free)，单位为字节
        """
        self.contexts[gpu_id].push()
        try:
            free, total = cuda.mem_get_info()
            return total, free
        finally:
            cuda.Context.pop()
    
    def get_optimal_batch_size(self, gpu_id, item_size):
        """
        计算最优的批处理大小
        
        Args:
            gpu_id: GPU ID
            item_size: 每个项目的大小（字节）
            
        Returns:
            最优批处理大小
        """
        # 获取GPU内存信息
        total, free = self.get_memory_info(gpu_id)
        
        # 保留25%的空闲内存，避免OOM错误
        usable_memory = free * 0.75
        
        # 计算可以容纳的项目数量
        max_items = int(usable_memory / item_size)
        
        # 确保批处理大小不超过硬件限制
        device_props = self.devices[self.gpu_ids.index(gpu_id)].get_attributes()
        max_threads = device_props[cuda.device_attribute.MAX_THREADS_PER_BLOCK]
        max_grid_x = device_props[cuda.device_attribute.MAX_GRID_DIM_X]
        
        max_hw_items = max_threads * max_grid_x
        
        # 取较小值作为批处理大小上限
        max_batch = min(max_items, max_hw_items)
        
        # 返回2的幂次方，方便GPU处理
        power = int(np.log2(max_batch))
        optimal_batch = 2 ** power
        
        return optimal_batch
    
    def get_device_info(self, gpu_id):
        """
        获取GPU设备信息
        
        Args:
            gpu_id: GPU ID
            
        Returns:
            设备信息字典
        """
        device = self.devices[self.gpu_ids.index(gpu_id)]
        return {
            'name': device.name(),
            'compute_capability': f"{device.compute_capability()[0]}.{device.compute_capability()[1]}",
            'total_memory': device.total_memory(),
            'clock_rate': device.get_attributes()[cuda.device_attribute.CLOCK_RATE],
            'multiprocessor_count': device.get_attributes()[cuda.device_attribute.MULTIPROCESSOR_COUNT],
            'max_threads_per_block': device.get_attributes()[cuda.device_attribute.MAX_THREADS_PER_BLOCK]
        }
    
    def get_optimal_block_config(self, gpu_id, num_items):
        """
        获取最优的CUDA块和网格配置
        
        Args:
            gpu_id: GPU ID
            num_items: 处理的项目数量
            
        Returns:
            (block_size, grid_size) 元组
        """
        device = self.devices[self.gpu_ids.index(gpu_id)]
        max_threads = device.get_attributes()[cuda.device_attribute.MAX_THREADS_PER_BLOCK]
        
        # 使用默认线程数或设备最大值中的较小值
        block_size = min(DEFAULT_THREADS_PER_BLOCK, max_threads)
        
        # 计算网格大小，确保能处理所有项目
        grid_size = (num_items + block_size - 1) // block_size
        
        # 不超过最大网格维度
        max_grid_dim = device.get_attributes()[cuda.device_attribute.MAX_GRID_DIM_X]
        grid_size = min(grid_size, max_grid_dim, DEFAULT_MAX_BLOCKS)
        
        return (block_size, grid_size)
    
    def execute_kernel(self, gpu_id, kernel_name, *args, **kwargs):
        """
        执行CUDA核函数
        
        Args:
            gpu_id: GPU ID
            kernel_name: 核函数名称
            *args: 传递给核函数的参数
            **kwargs: 其他参数，包括block和grid配置
            
        Returns:
            执行结果
        """
        self.contexts[gpu_id].push()
        
        try:
            # 获取核函数
            kernel_func = self.functions[gpu_id][kernel_name]
            
            # 执行核函数
            if 'block' in kwargs and 'grid' in kwargs:
                kernel_func(*args, block=kwargs['block'], grid=kwargs['grid'])
            else:
                # 如果未指定块和网格配置，使用默认值
                num_items = kwargs.get('num_items', 1)
                block_size, grid_size = self.get_optimal_block_config(gpu_id, num_items)
                kernel_func(*args, block=(block_size, 1, 1), grid=(grid_size, 1))
        
        finally:
            # 弹出上下文
            cuda.Context.pop()
    
    def allocate_memory(self, gpu_id, size):
        """
        在GPU上分配内存
        
        Args:
            gpu_id: GPU ID
            size: 分配的字节数
            
        Returns:
            CUDA设备内存对象
        """
        self.contexts[gpu_id].push()
        try:
            return cuda.mem_alloc(size)
        finally:
            cuda.Context.pop()
    
    def copy_to_device(self, gpu_id, host_array, device_mem):
        """
        将主机数据复制到设备内存
        
        Args:
            gpu_id: GPU ID
            host_array: 主机数组（NumPy数组）
            device_mem: 设备内存对象
        """
        self.contexts[gpu_id].push()
        try:
            cuda.memcpy_htod(device_mem, host_array)
        finally:
            cuda.Context.pop()
    
    def copy_from_device(self, gpu_id, device_mem, host_array):
        """
        将设备内存数据复制到主机
        
        Args:
            gpu_id: GPU ID
            device_mem: 设备内存对象
            host_array: 主机数组（NumPy数组）
        """
        self.contexts[gpu_id].push()
        try:
            cuda.memcpy_dtoh(host_array, device_mem)
        finally:
            cuda.Context.pop()
    
    def get_device_name(self, gpu_id):
        """获取指定GPU的设备名称
        Args:
            gpu_id (int): GPU设备ID
        Returns:
            str: GPU设备名称
        """
        if gpu_id not in self.gpu_ids:
            raise ValueError(f"Invalid GPU ID: {gpu_id}")
        return self.devices[self.gpu_ids.index(gpu_id)].name() 