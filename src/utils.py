#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具函数模块
"""

import os
import json
import math
import itertools
from pathlib import Path

def format_speed(speed):
    """
    格式化速度显示
    
    Args:
        speed: 每秒尝试次数
        
    Returns:
        格式化的速度字符串
    """
    if speed < 1000:
        return f"{speed:.2f} 次/秒"
    elif speed < 1000000:
        return f"{speed/1000:.2f} K次/秒"
    elif speed < 1000000000:
        return f"{speed/1000000:.2f} M次/秒"
    else:
        return f"{speed/1000000000:.2f} G次/秒"

def save_checkpoint(checkpoint_file, data):
    """
    保存检查点
    
    Args:
        checkpoint_file: 检查点文件路径
        data: 要保存的数据
    """
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def load_checkpoint(checkpoint_file):
    """
    加载检查点
    
    Args:
        checkpoint_file: 检查点文件路径
        
    Returns:
        加载的检查点数据
    """
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def estimate_combinations(charset, min_length, max_length, mask=None, dict_file=None, use_years=False):
    """
    估算可能的密码组合数量
    
    Args:
        charset: 字符集
        min_length: 最小密码长度
        max_length: 最大密码长度
        mask: 掩码模式
        dict_file: 字典文件路径
        use_years: 是否使用年份
        
    Returns:
        估计的组合总数
    """
    if dict_file:
        # 字典攻击，统计字典文件中的行数
        count = sum(1 for _ in open(dict_file, 'r', encoding='utf-8', errors='ignore'))
        
        # 如果使用年份，需要乘以年份数量
        if use_years:
            count *= (2026 - 2020)
            
        return count
    
    elif mask:
        # 掩码攻击
        from src.config import MASK_SYMBOLS
        
        # 解析掩码
        combinations = 1
        i = 0
        while i < len(mask):
            if mask[i] == '?' and i + 1 < len(mask):
                symbol = mask[i:i+2]
                if symbol in MASK_SYMBOLS:
                    combinations *= len(MASK_SYMBOLS[symbol])
                    i += 2
                    continue
            # 如果不是掩码符号，只有一种可能
            combinations *= 1
            i += 1
        
        return combinations
    
    else:
        # 暴力破解
        total = 0
        charset_len = len(charset)
        
        for length in range(min_length, max_length + 1):
            total += charset_len ** length
        
        # 如果使用年份，添加额外的组合
        if use_years:
            years_combinations = 0
            years_count = 2026 - 2020
            
            # 估算含年份的组合数量（简化计算）
            for length in range(min_length - 4, max_length - 3):  # 减去年份长度
                if length >= 1:  # 至少有一个其他字符
                    years_combinations += charset_len ** length * years_count
            
            total += years_combinations
        
        return total

def generate_password_batch(charset, length, start_idx, batch_size):
    """
    生成一批特定长度的密码
    
    Args:
        charset: 字符集
        length: 密码长度
        start_idx: 起始索引
        batch_size: 批量大小
        
    Returns:
        生成的密码列表
    """
    charset_len = len(charset)
    passwords = []
    
    for i in range(start_idx, min(start_idx + batch_size, charset_len ** length)):
        # 将索引转换为基于字符集的数字系统
        password = []
        idx = i
        for _ in range(length):
            password.append(charset[idx % charset_len])
            idx //= charset_len
        passwords.append(''.join(reversed(password)))
    
    return passwords

def parse_mask(mask, charset_map):
    """
    解析掩码为字符集列表
    
    Args:
        mask: 掩码字符串，如 ?a?d?d?d
        charset_map: 字符集映射
        
    Returns:
        字符集列表，每个位置一个字符集
    """
    charsets = []
    i = 0
    
    while i < len(mask):
        if mask[i] == '?' and i + 1 < len(mask):
            symbol = mask[i:i+2]
            if symbol in charset_map:
                charsets.append(charset_map[symbol])
                i += 2
                continue
        # 如果是固定字符
        charsets.append(mask[i])
        i += 1
    
    return charsets

def get_position_from_index(index, charset_lengths):
    """
    将索引转换为多进制位置表示
    
    Args:
        index: 线性索引
        charset_lengths: 每个位置的字符集长度列表
        
    Returns:
        位置数组，表示每个位置的字符索引
    """
    position = []
    for length in reversed(charset_lengths):
        position.insert(0, index % length)
        index //= length
    return position

def get_index_from_position(position, charset_lengths):
    """
    将多进制位置转换为线性索引
    
    Args:
        position: 位置数组
        charset_lengths: 每个位置的字符集长度列表
        
    Returns:
        线性索引
    """
    index = 0
    for i, pos in enumerate(position):
        index = index * charset_lengths[i] + pos
    return index

def calculate_work_division(total_combinations, num_gpus):
    """
    计算工作在多个GPU之间的分配
    
    Args:
        total_combinations: 总组合数
        num_gpus: GPU数量
        
    Returns:
        每个GPU的工作区间列表 [(start1, end1), (start2, end2), ...]
    """
    base_size = total_combinations // num_gpus
    remainder = total_combinations % num_gpus
    
    divisions = []
    start = 0
    
    for i in range(num_gpus):
        # 前remainder个GPU多分配一个任务
        size = base_size + (1 if i < remainder else 0)
        end = start + size
        divisions.append((start, end))
        start = end
    
    return divisions

def chunks(iterable, size):
    """
    将可迭代对象分割为指定大小的块
    
    Args:
        iterable: 可迭代对象
        size: 块大小
        
    Returns:
        生成器，每次生成一个块
    """
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, size))
        if not chunk:
            break
        yield chunk 