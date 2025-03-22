#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAR密码破解器核心实现
"""

import os
import time
import itertools
import logging
import multiprocessing as mp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pycuda.driver as cuda
from pycuda.compiler import SourceModule
import rarfile

from src.config import (
    MASK_SYMBOLS, PASSWORD_BATCH_SIZE, YEARS_RANGE, 
    DEFAULT_THREADS_PER_BLOCK, DEFAULT_MAX_BLOCKS
)
from src.utils import (
    parse_mask, get_position_from_index, get_index_from_position,
    calculate_work_division, chunks, generate_password_batch
)
from src.cuda_kernels import CUDA_KERNEL_CODE

# 根据操作系统设置正确的路径分隔符和UnRAR工具路径
import platform

if platform.system() == 'Windows':
    rarfile.UNRAR_TOOL = "C:\\Program Files\\WinRAR\\UnRAR.exe"  # Windows路径
    rarfile.PATH_SEP = '\\'
else:
    # Linux或macOS - 需要从PATH中查找unrar
    import shutil
    unrar_path = shutil.which('unrar')
    if unrar_path:
        rarfile.UNRAR_TOOL = unrar_path
    else:
        # 尝试常见位置
        for path in ['/usr/bin/unrar', '/usr/local/bin/unrar', '/bin/unrar']:
            if os.path.exists(path):
                rarfile.UNRAR_TOOL = path
                break
    rarfile.PATH_SEP = '/'

class RARCracker:
    """
    RAR密码破解器类
    """
    def __init__(self, rar_file, gpu_manager, **kwargs):
        """
        初始化RAR破解器
        
        Args:
            rar_file: RAR文件路径
            gpu_manager: GPU管理器
            mask: 密码掩码
            min_length: 最小密码长度
            max_length: 最大密码长度
            dict_file: 字典文件路径
            batch_size: 每批处理的密码数量
            threads_per_block: CUDA每个块的线程数
            concurrent_batches: 并行处理的批次数
            shared_mem_size: 每块共享内存大小
        """
        self.rar_file = rar_file
        self.gpu_manager = gpu_manager
        self.contexts = []  # 添加contexts属性
        
        # 设置参数
        self.mask = kwargs.get('mask')
        self.min_length = kwargs.get('min_length', 8)
        self.max_length = kwargs.get('max_length', 12)
        self.dict_file = kwargs.get('dict_file')
        self.batch_size = kwargs.get('batch_size', 5000000)
        self.threads_per_block = kwargs.get('threads_per_block', 1024)
        self.concurrent_batches = kwargs.get('concurrent_batches', 2)
        self.shared_mem_size = kwargs.get('shared_mem_size')
        
        # 初始化状态
        self.current_position = None
        self.found_password = None
        
        # 初始化CUDA
        self._init_cuda()
        
        # 验证RAR文件
        self._validate_rar_file()
    
    def _init_cuda(self):
        """初始化CUDA环境"""
        try:
            import os
            import pycuda.driver as cuda
            
            # 创建临时文件夹
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 保存CUDA代码到文件
            cuda_file = os.path.abspath(os.path.join(temp_dir, "kernel.cu"))
            with open(cuda_file, 'w') as f:
                f.write(CUDA_KERNEL_CODE)
            
            # 手动编译CUDA代码为PTX
            ptx_file = os.path.abspath(os.path.join(temp_dir, "kernel.ptx"))
            import subprocess
            logging.info(f"编译CUDA核心: {cuda_file} -> {ptx_file}")
            
            compile_result = subprocess.run(
                ["nvcc", "--ptx", "-o", ptx_file, cuda_file],
                capture_output=True, 
                text=True,
                cwd=temp_dir
            )
            
            if compile_result.returncode != 0:
                logging.error(f"NVCC编译错误: {compile_result.stderr}")
                raise RuntimeError(f"NVCC编译失败: {compile_result.stderr}")
            
            # 加载PTX文件
            logging.info(f"加载PTX文件: {ptx_file}")
            
            # 初始化上下文 - 关键修改部分
            self.contexts = []  # 确保contexts已初始化
            for gpu_id in self.gpu_manager.gpu_ids:
                device = cuda.Device(gpu_id)
                context = device.make_context()
                self.contexts.append(context)
                
                # 在第一个GPU上下文中加载PTX模块
                if gpu_id == self.gpu_manager.gpu_ids[0]:
                    mod = cuda.module_from_file(ptx_file)
                    self.check_password_kernel = mod.get_function("check_rar_password")
                
                # 立即弹出上下文，避免堆叠
                context.pop()
            
            # 配置线程块
            self.block_size = (min(1024, self.threads_per_block), 1, 1)
            self.grid_size = (
                (self.batch_size + self.block_size[0] - 1) // self.block_size[0],
                1,
                1
            )
            
        except Exception as e:
            logging.error(f"CUDA初始化失败: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            raise
    
    def _validate_rar_file(self):
        """验证RAR文件是否有效且有密码保护"""
        try:
            rf = rarfile.RarFile(self.rar_file)
            self.is_encrypted = rf.needs_password()
            if not self.is_encrypted:
                raise ValueError(f"RAR文件 '{self.rar_file}' 未加密，不需要密码")
            
            # 从RAR文件读取头部数据，用于CUDA核函数中的验证
            # 这里简化处理，实际应该读取正确的加密头部数据
            with open(self.rar_file, 'rb') as f:
                self.rar_header = f.read(32)  # 读取前32字节作为头部
            
        except rarfile.Error as e:
            raise ValueError(f"无效的RAR文件: {e}")
    
    def check_password(self, password):
        """
        在CPU上验证单个密码
        
        Args:
            password: 要验证的密码
            
        Returns:
            是否匹配
        """
        try:
            rf = rarfile.RarFile(self.rar_file)
            # 使用 /tmp 目录或当前目录作为临时提取位置
            extract_path = "/tmp" if os.path.exists("/tmp") else "./temp"
            rf.extractall(path=extract_path, pwd=password)
            return True
        except rarfile.PasswordRequired:
            # 密码错误
            return False
        except rarfile.RarCRCError:
            # CRC错误通常表示密码错误
            return False
        except rarfile.RarCannotExec:
            # 无法执行UnRAR工具，尝试只测试文件而不提取
            try:
                # 尝试测试压缩包
                rf = rarfile.RarFile(self.rar_file)
                rf.testrar(pwd=password)
                return True
            except:
                return False
        except Exception as e:
            logging.error(f"验证密码时出错: {e}")
            return False
    
    def run(self, start_position=None):
        """运行密码破解过程"""
        try:
            # 根据攻击类型选择执行方法
            if self.mask:
                # 掩码攻击
                for batch_result in self._run_mask_attack(start_position):
                    yield batch_result
            elif self.dict_file:
                # 字典攻击
                for batch_result in self._run_dictionary_attack(start_position):
                    yield batch_result
            else:
                # 默认暴力破解
                for batch_result in self._run_bruteforce_attack(start_position):
                    yield batch_result
        finally:
            # 确保所有上下文都被清理
            self._cleanup_contexts()
    
    def _run_bruteforce_attack(self, start_position=None):
        """
        执行暴力破解
        
        Args:
            start_position: 起始位置
            
        Yields:
            字典，包含当前状态和结果
        """
        # 为每个GPU分配工作
        num_gpus = len(self.gpu_manager.gpu_ids)
        
        # 多GPU并行处理
        with ThreadPoolExecutor(max_workers=num_gpus) as executor:
            futures = []
            
            for length in range(self.min_length, self.max_length + 1):
                total_combinations = len(self.gpu_manager.charset) ** length
                
                # 计算每个GPU的工作范围
                work_ranges = calculate_work_division(total_combinations, num_gpus)
                
                # 为每个GPU提交任务
                for gpu_idx, (start, end) in enumerate(work_ranges):
                    # 如果指定了起始位置，且在当前长度范围内
                    if start_position and isinstance(start_position, tuple) and start_position[0] == length:
                        if start_position[1] >= start:
                            start = start_position[1]
                        
                    future = executor.submit(
                        self._gpu_bruteforce_task,
                        gpu_idx, self.gpu_manager.charset, length, start, end
                    )
                    futures.append(future)
            
            # 处理完成的任务
            for future in as_completed(futures):
                result = future.result()
                if result and result.get('password'):
                    # 找到密码，提前结束
                    self.found_password = result['password']
                    yield result
                    return
                
                # 返回进度信息
                if result:
                    yield result
    
    def _gpu_bruteforce_task(self, gpu_idx, charset, length, start, end):
        """
        单个GPU执行的暴力破解任务
        
        Args:
            gpu_idx: GPU索引
            charset: 字符集
            length: 密码长度
            start: 起始索引
            end: 结束索引
            
        Returns:
            结果字典
        """
        # 激活此GPU的上下文
        self.contexts[gpu_idx].push()
        
        # 最大块数量
        max_blocks = min(DEFAULT_MAX_BLOCKS, (end - start + self.threads_per_block - 1) // self.threads_per_block)
        
        attempts = 0
        batch_size = min(PASSWORD_BATCH_SIZE, end - start)
        
        for batch_start in range(start, end, batch_size):
            batch_end = min(batch_start + batch_size, end)
            current_batch_size = batch_end - batch_start
            
            # 生成当前批次的密码
            passwords = generate_password_batch(charset, length, batch_start, current_batch_size)
            
            # 准备CUDA输入数据
            password_data = ''.join(passwords)
            password_lengths = [len(p) for p in passwords]
            
            # 分配CUDA内存
            passwords_gpu = cuda.mem_alloc(len(password_data))
            lengths_gpu = cuda.mem_alloc(len(password_lengths) * 4)  # int = 4 bytes
            header_gpu = cuda.mem_alloc(len(self.rar_header))
            results_gpu = cuda.mem_alloc(len(passwords) * 4)  # int = 4 bytes
            
            # 拷贝数据到GPU
            cuda.memcpy_htod(passwords_gpu, np.array([ord(c) for c in password_data], dtype=np.uint8))
            cuda.memcpy_htod(lengths_gpu, np.array(password_lengths, dtype=np.int32))
            cuda.memcpy_htod(header_gpu, np.array([b for b in self.rar_header], dtype=np.uint8))
            
            # 调用CUDA核函数
            block_size = (self.threads_per_block, 1, 1)
            grid_size = (min(max_blocks, (current_batch_size + self.threads_per_block - 1) // self.threads_per_block), 1)
            
            self.check_password_kernel(
                passwords_gpu, lengths_gpu, np.int32(len(passwords)),
                header_gpu, np.int32(len(self.rar_header)),
                results_gpu,
                block=block_size, grid=grid_size
            )
            
            # 获取结果
            results = np.zeros(len(passwords), dtype=np.int32)
            cuda.memcpy_dtoh(results, results_gpu)
            
            # 释放GPU内存
            passwords_gpu.free()
            lengths_gpu.free()
            header_gpu.free()
            results_gpu.free()
            
            # 检查结果
            for i, password in enumerate(passwords):
                if results[i] == 1:
                    # 在CPU上再次验证密码
                    if self.check_password(password):
                        # 弹出上下文
                        self.contexts[gpu_idx].pop()
                        return {
                            'password': password,
                            'attempts': attempts + i + 1,
                            'position': (length, batch_start + i)
                        }
            
            # 更新状态
            attempts += current_batch_size
            self.current_position = (length, batch_end)
            
            # 每批次返回一次状态
            if current_batch_size > 0:
                # 弹出上下文
                cuda.Context.pop()
                return {
                    'password': None,
                    'attempts': current_batch_size,
                    'position': (length, batch_end)
                }
        
        # 弹出上下文
        cuda.Context.pop()
        return {
            'password': None,
            'attempts': attempts,
            'position': (length, end)
        }
    
    def _run_mask_attack(self, start_position=None):
        """
        执行掩码攻击
        
        Args:
            start_position: 起始位置
            
        Yields:
            字典，包含当前状态和结果
        """
        # 解析掩码为字符集列表
        charsets = parse_mask(self.mask, MASK_SYMBOLS)
        charset_lengths = [len(charset) if isinstance(charset, str) and len(charset) > 1 else 1 
                          for charset in charsets]
        
        # 计算总组合数
        total_combinations = 1
        for length in charset_lengths:
            total_combinations *= length
        
        # 为每个GPU分配工作
        num_gpus = len(self.gpu_manager.gpu_ids)
        work_ranges = calculate_work_division(total_combinations, num_gpus)
        
        # 多GPU并行处理
        with ThreadPoolExecutor(max_workers=num_gpus) as executor:
            futures = []
            
            for gpu_idx, (start, end) in enumerate(work_ranges):
                # 如果指定了起始位置
                if start_position and isinstance(start_position, list):
                    # 将起始位置转换为线性索引
                    start_idx = get_index_from_position(start_position, charset_lengths)
                    if start_idx >= start:
                        start = start_idx
                
                future = executor.submit(
                    self._gpu_mask_task,
                    gpu_idx, charsets, charset_lengths, start, end
                )
                futures.append(future)
            
            # 处理完成的任务
            for future in as_completed(futures):
                result = future.result()
                if result and result.get('password'):
                    # 找到密码，提前结束
                    self.found_password = result['password']
                    yield result
                    return
                
                # 返回进度信息
                if result:
                    yield result
    
    def _gpu_mask_task(self, gpu_idx, charsets, charset_lengths, start, end):
        """
        单个GPU执行的掩码攻击任务
        
        Args:
            gpu_idx: GPU索引
            charsets: 字符集列表
            charset_lengths: 每个位置的字符集长度
            start: 起始索引
            end: 结束索引
            
        Returns:
            结果字典
        """
        # 激活此GPU的上下文
        try:
            self.contexts[gpu_idx].push()
            
            attempts = 0
            batch_size = min(PASSWORD_BATCH_SIZE, end - start)
            
            for batch_start in range(start, end, batch_size):
                batch_end = min(batch_start + batch_size, end)
                current_batch_size = batch_end - batch_start
                
                # 生成当前批次的密码
                passwords = []
                for i in range(batch_start, batch_end):
                    # 将线性索引转换为多进制位置
                    position = get_position_from_index(i, charset_lengths)
                    
                    # 根据掩码和位置生成密码
                    password = []
                    for pos, charset in zip(position, charsets):
                        if isinstance(charset, str) and len(charset) > 1:
                            password.append(charset[pos])
                        else:
                            password.append(charset)  # 固定字符
                    
                    passwords.append(''.join(password))
                
                # 与暴力破解相同的CUDA处理逻辑
                # ...（与 _gpu_bruteforce_task 类似的处理逻辑）
                
                # 这里简化处理，实际应该复用 _gpu_bruteforce_task 中的CUDA处理代码
                for i, password in enumerate(passwords):
                    if self.check_password(password):
                        # 弹出上下文
                        self.contexts[gpu_idx].pop()
                        return {
                            'password': password,
                            'attempts': attempts + i + 1,
                            'position': get_position_from_index(batch_start + i, charset_lengths)
                        }
                
                # 更新状态
                attempts += current_batch_size
                self.current_position = get_position_from_index(batch_end - 1, charset_lengths)
                
                # 每批次返回一次状态
                if current_batch_size > 0:
                    return {
                        'password': None,
                        'attempts': current_batch_size,
                        'position': self.current_position
                    }
            
            return {
                'password': None,
                'attempts': attempts,
                'position': get_position_from_index(end - 1, charset_lengths)
            }
        finally:
            # 确保上下文被弹出
            try:
                cuda.Context.pop()
            except:
                pass
    
    def _run_dictionary_attack(self, start_position=None):
        """
        执行字典攻击
        
        Args:
            start_position: 起始行号（断点续跑）
            
        Yields:
            字典，包含当前状态和结果
        """
        # 读取字典文件
        with open(self.dict_file, 'r', encoding='utf-8', errors='ignore') as f:
            # 如果指定了起始位置，跳过之前的行
            if start_position and isinstance(start_position, int):
                for _ in range(start_position):
                    next(f, None)
            
            # 按批处理密码
            line_number = start_position if start_position else 0
            
            # 使用线程池并行处理批次密码
            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                for password_batch in chunks(f, PASSWORD_BATCH_SIZE):
                    # 移除每行结尾的换行符
                    password_batch = [p.strip() for p in password_batch]
                    
                    # 如果需要加入年份
                    if self.gpu_manager.use_years:
                        expanded_batch = []
                        for password in password_batch:
                            expanded_batch.append(password)  # 原始密码
                            # 添加年份后缀
                            for year in YEARS_RANGE:
                                expanded_batch.append(f"{password}{year}")
                        password_batch = expanded_batch
                    
                    # 准备CUDA处理
                    futures = []
                    batch_size_per_gpu = (len(password_batch) + len(self.gpu_manager.gpu_ids) - 1) // len(self.gpu_manager.gpu_ids)
                    
                    for gpu_idx, gpu_batch in enumerate(chunks(password_batch, batch_size_per_gpu)):
                        future = executor.submit(
                            self._gpu_dictionary_task,
                            gpu_idx, gpu_batch
                        )
                        futures.append(future)
                    
                    # 处理完成的任务
                    for future in as_completed(futures):
                        result = future.result()
                        if result and result.get('password'):
                            # 找到密码，提前结束
                            self.found_password = result['password']
                            yield result
                            return
                    
                    # 更新进度
                    line_number += len(password_batch)
                    self.current_position = line_number
                    
                    yield {
                        'password': None,
                        'attempts': len(password_batch),
                        'position': line_number
                    }
    
    def _gpu_dictionary_task(self, gpu_idx, password_batch):
        """
        单个GPU执行的字典攻击任务
        
        Args:
            gpu_idx: GPU索引
            password_batch: 密码批次
            
        Returns:
            结果字典
        """
        # 激活此GPU的上下文
        self.contexts[gpu_idx].push()
        
        # 这里简化处理，实际应该使用CUDA加速
        for i, password in enumerate(password_batch):
            if self.check_password(password):
                # 弹出上下文
                self.contexts[gpu_idx].pop()
                return {
                    'password': password,
                    'attempts': i + 1,
                    'position': None
                }
        
        # 弹出上下文
        cuda.Context.pop()
        return {
            'password': None,
            'attempts': len(password_batch),
            'position': None
        }
    
    def _cleanup_contexts(self):
        """清理所有CUDA上下文"""
        try:
            # 清理上下文堆栈
            while True:
                try:
                    ctx = cuda.Context.get_current()
                    if ctx is None:
                        break
                    ctx.pop()
                except cuda.Error:
                    break
                
            # 分离所有上下文
            if hasattr(self, 'contexts'):
                for context in self.contexts:
                    try:
                        context.detach()
                    except:
                        pass
        except Exception as e:
            logging.error(f"清理CUDA上下文时出错: {e}")
    
    def __del__(self):
        """析构函数，确保清理CUDA资源"""
        self._cleanup_contexts() 