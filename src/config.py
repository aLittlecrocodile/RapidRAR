#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置常量和默认值
"""

# 字符集
LOWERCASE_CHARS = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGIT_CHARS = "0123456789"
SPECIAL_CHARS = "@#!$%^"

DEFAULT_SPECIAL_CHARS = SPECIAL_CHARS
DEFAULT_CHARSET = LOWERCASE_CHARS + UPPERCASE_CHARS + DIGIT_CHARS + SPECIAL_CHARS

# 年份范围（用于生成可能的日期密码组合）
YEARS_RANGE = list(range(2020, 2026))  # 2020-2025

# CUDA相关配置
DEFAULT_THREADS_PER_BLOCK = 256
DEFAULT_MAX_BLOCKS = 1024

# RAR验证相关参数
RAR_HEADER_SIZE = 32  # RAR文件头部大小，用于验证密码

# 掩码符号定义
MASK_SYMBOLS = {
    '?a': LOWERCASE_CHARS + UPPERCASE_CHARS + DIGIT_CHARS + SPECIAL_CHARS,  # 所有字符
    '?l': LOWERCASE_CHARS,  # 小写字母
    '?u': UPPERCASE_CHARS,  # 大写字母
    '?d': DIGIT_CHARS,      # 数字
    '?s': SPECIAL_CHARS,    # 特殊字符
    '?h': "0123456789abcdef", # 十六进制
}

# 性能相关配置
PASSWORD_BATCH_SIZE = 10000  # 每批处理的密码数量
MAX_PASSWORDS_IN_MEMORY = 1000000  # 内存中最大的密码数量

# 检查点配置
CHECKPOINT_INTERVAL = 60  # 检查点保存间隔（秒）

# 日志配置
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 