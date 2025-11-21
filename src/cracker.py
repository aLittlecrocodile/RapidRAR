#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAR密码破解器核心实现
"""

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import rarfile
import numpy as np

from src.config import (
    MASK_SYMBOLS, PASSWORD_BATCH_SIZE, YEARS_RANGE
)
from src.utils import (
    parse_mask, get_position_from_index, get_index_from_position,
    calculate_work_division, chunks, generate_password_batch
)
from src.backends import get_backend

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
        found = False
        for path in ['/usr/bin/unrar', '/usr/local/bin/unrar', '/bin/unrar']:
            if os.path.exists(path):
                rarfile.UNRAR_TOOL = path
                found = True
                break
        
        # 如果没找到unrar，尝试bsdtar
        if not found:
            bsdtar_path = shutil.which('bsdtar')
            if bsdtar_path:
                rarfile.UNRAR_TOOL = bsdtar_path
    rarfile.PATH_SEP = '/'

class RARCracker:
    """
    RAR密码破解器类
    """
    def __init__(self, rar_file, **kwargs):
        """
        初始化RAR破解器
        
        Args:
            rar_file: RAR文件路径
            mask: 密码掩码
            min_length: 最小密码长度
            max_length: 最大密码长度
            dict_file: 字典文件路径
            batch_size: 每批处理的密码数量
            backend: 后端名称 ('auto', 'cpu', 'cuda')
            gpu_id: GPU ID (if using cuda)
        """
        self.rar_file = rar_file
        
        # 设置参数
        self.mask = kwargs.get('mask')
        self.min_length = kwargs.get('min_length', 8)
        self.max_length = kwargs.get('max_length', 12)
        self.dict_file = kwargs.get('dict_file')
        self.batch_size = kwargs.get('batch_size', 100000) # Reduced default for CPU safety
        self.backend_name = kwargs.get('backend', 'auto')
        self.gpu_id = kwargs.get('gpu_id', 0)
        self.charset = kwargs.get('charset', '')
        
        # 初始化状态
        self.current_position = None
        self.found_password = None
        
        # 初始化后端
        self.backend = get_backend(self.backend_name, gpu_id=self.gpu_id)
        self.backend.init()
        
        # 验证RAR文件
        self._validate_rar_file()
        
        # 如果后端支持，设置RAR头部
        if hasattr(self.backend, 'set_rar_header'):
             with open(self.rar_file, 'rb') as f:
                header = f.read(32) # Simplified
                self.backend.set_rar_header(header)

    def _validate_rar_file(self):
        """验证RAR文件是否有效且有密码保护"""
        try:
            rf = rarfile.RarFile(self.rar_file)
            if not rf.needs_password():
                raise ValueError(f"RAR文件 '{self.rar_file}' 未加密，不需要密码")
        except rarfile.Error as e:
            raise ValueError(f"无效的RAR文件: {e}")
    
    def run(self, start_position=None):
        """运行密码破解过程"""
        try:
            if self.mask:
                for batch_result in self._run_mask_attack(start_position):
                    yield batch_result
            elif self.dict_file:
                for batch_result in self._run_dictionary_attack(start_position):
                    yield batch_result
            else:
                for batch_result in self._run_bruteforce_attack(start_position):
                    yield batch_result
        finally:
            self.backend.cleanup()
    
    def _run_bruteforce_attack(self, start_position=None):
        """执行暴力破解"""
        # 简单实现：单线程控制循环，后端负责并行检查
        # 如果是CPU后端，backend.check_passwords内部会并行
        
        for length in range(self.min_length, self.max_length + 1):
            total_combinations = len(self.charset) ** length
            
            start_idx = 0
            if start_position and isinstance(start_position, tuple) and start_position[0] == length:
                start_idx = start_position[1]
                
            for batch_start in range(start_idx, total_combinations, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_combinations)
                current_batch_size = batch_end - batch_start
                
                # 生成密码
                passwords = generate_password_batch(self.charset, length, batch_start, current_batch_size)
                
                # 检查密码
                found = self.backend.check_passwords(passwords, self.rar_file)
                
                if found:
                    self.found_password = found
                    yield {
                        'password': found,
                        'attempts': current_batch_size, # approximate
                        'position': (length, batch_end)
                    }
                    return
                
                yield {
                    'password': None,
                    'attempts': current_batch_size,
                    'position': (length, batch_end)
                }

    def _run_mask_attack(self, start_position=None):
        """执行掩码攻击"""
        charsets = parse_mask(self.mask, MASK_SYMBOLS)
        charset_lengths = [len(c) if isinstance(c, str) and len(c) > 1 else 1 for c in charsets]
        
        total_combinations = 1
        for l in charset_lengths:
            total_combinations *= l
            
        start_idx = 0
        if start_position and isinstance(start_position, list):
             start_idx = get_index_from_position(start_position, charset_lengths)
             
        for batch_start in range(start_idx, total_combinations, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_combinations)
            current_batch_size = batch_end - batch_start
            
            passwords = []
            for i in range(batch_start, batch_end):
                position = get_position_from_index(i, charset_lengths)
                pwd = []
                for pos, charset in zip(position, charsets):
                    if isinstance(charset, str) and len(charset) > 1:
                        pwd.append(charset[pos])
                    else:
                        pwd.append(charset)
                passwords.append(''.join(pwd))
            
            found = self.backend.check_passwords(passwords, self.rar_file)
            
            if found:
                self.found_password = found
                yield {
                    'password': found,
                    'attempts': current_batch_size,
                    'position': get_position_from_index(batch_end, charset_lengths)
                }
                return
                
            yield {
                'password': None,
                'attempts': current_batch_size,
                'position': get_position_from_index(batch_end, charset_lengths)
            }

    def _run_dictionary_attack(self, start_position=None):
        """执行字典攻击"""
        with open(self.dict_file, 'r', encoding='utf-8', errors='ignore') as f:
            if start_position:
                for _ in range(start_position):
                    next(f, None)
            
            line_number = start_position if start_position else 0
            
            for password_batch in chunks(f, self.batch_size):
                password_batch = [p.strip() for p in password_batch]
                
                # Check passwords
                found = self.backend.check_passwords(password_batch, self.rar_file)
                
                if found:
                    self.found_password = found
                    yield {
                        'password': found,
                        'attempts': len(password_batch),
                        'position': line_number + len(password_batch)
                    }
                    return
                
                line_number += len(password_batch)
                yield {
                    'password': None,
                    'attempts': len(password_batch),
                    'position': line_number
                }