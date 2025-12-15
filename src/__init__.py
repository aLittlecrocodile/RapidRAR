#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
ZipCracker包初始化文件
"""

import logging
from pathlib import Path
from .cracker import RARCracker
from .gpu_manager import GPUManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 确保目录结构
def ensure_dirs():
    """确保必要的目录存在"""
    # 检查点目录
    checkpoint_dir = Path('checkpoints')
    if not checkpoint_dir.exists():
        checkpoint_dir.mkdir(parents=True)
    
    # 临时目录
    temp_dir = Path('temp')
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True)

# 当导入包时运行
ensure_dirs()

__all__ = ['RARCracker', 'GPUManager']
 