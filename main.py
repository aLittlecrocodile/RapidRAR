#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import time
import json
from pathlib import Path
import traceback
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from src.cracker import RARCracker
from src.utils import estimate_combinations, format_speed, load_checkpoint, save_checkpoint
from src.config import DEFAULT_CHARSET, DEFAULT_SPECIAL_CHARS, YEARS_RANGE
from src.gpu_manager import GPUManager
import pycuda.driver as cuda

console = Console()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='GPU加速的RAR密码恢复工具')
    
    # 基本参数
    parser.add_argument('--rar_file', required=True, help='RAR文件路径')
    parser.add_argument('--min_length', type=int, default=8, help='最小密码长度')
    parser.add_argument('--max_length', type=int, default=12, help='最大密码长度')
    
    # 字符集参数
    parser.add_argument('--charset', default=None, help='自定义字符集')
    parser.add_argument('--use_lowercase', action='store_true', help='使用小写字母')
    parser.add_argument('--use_uppercase', action='store_true', help='使用大写字母')
    parser.add_argument('--use_digits', action='store_true', help='使用数字')
    parser.add_argument('--use_special', action='store_true', help='使用特殊字符')
    parser.add_argument('--use_years', action='store_true', help='插入年份（2020-2025）')
    
    # 攻击方式
    parser.add_argument('--mask', default=None, help='密码掩码，例如 ?a?a?a?a?d?d?d?d')
    parser.add_argument('--dict', default=None, help='字典文件路径')
    
    # 硬件参数 - 添加更多性能优化选项
    parser.add_argument('--gpu', type=int, default=0, help='使用的GPU ID')
    parser.add_argument('--threads_per_block', type=int, default=256, help='CUDA每个块的线程数')
    parser.add_argument('--batch_size', type=int, default=10000000, help='每批处理的密码数量')
    parser.add_argument('--concurrent_batches', type=int, default=2, help='并行批次数')
    parser.add_argument('--shared_mem_size', type=int, default=None, help='每块共享内存大小(字节)')
    
    # 其他参数
    parser.add_argument('--checkpoint', default='checkpoint.json', help='检查点文件路径')
    parser.add_argument('--resume', action='store_true', help='从检查点恢复')
    parser.add_argument('--update_interval', type=float, default=1.0, help='进度更新间隔（秒）')
    
    return parser.parse_args()

def get_charset(args):
    """根据参数生成字符集"""
    if args.charset:
        return args.charset
    
    charset = ""
    if args.use_lowercase:
        charset += "abcdefghijklmnopqrstuvwxyz"
    if args.use_uppercase:
        charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if args.use_digits:
        charset += "0123456789"
    if args.use_special:
        charset += DEFAULT_SPECIAL_CHARS
    
    # 如果没有选择任何字符集，使用默认值
    if not charset:
        charset = DEFAULT_CHARSET
    
    return charset

def main():
    """主程序入口"""
    args = parse_arguments()
    
    # 初始化变量 - 添加这两行
    total_attempts = 0
    found_password = None
    
    try:
        # 验证文件存在
        if not os.path.exists(args.rar_file):
            console.print(f"[bold red]错误: 文件 {args.rar_file} 不存在[/bold red]")
            return
        
        # 初始化CUDA
        try:
            cuda.init()
        except cuda.Error:
            pass  # 已初始化则忽略
        
        console.print(f"[bold green]正在使用GPU进行密码恢复...[/bold green]")
        device = cuda.Device(args.gpu)
        device_info = device.get_attributes()
        
        # 显示GPU信息
        console.print(f"[bold]GPU信息:[/bold] {device.name()}")
        console.print(f"[bold]显存大小:[/bold] {device.total_memory() / (1024**3):.2f} GB")
        console.print(f"[bold]CUDA核心数:[/bold] {device_info[cuda.device_attribute.MULTIPROCESSOR_COUNT] * 64}")
        console.print(f"[bold]最大线程数/块:[/bold] {device_info[cuda.device_attribute.MAX_THREADS_PER_BLOCK]}")
        
        # 性能优化建议
        recommended_threads = min(1024, device_info[cuda.device_attribute.MAX_THREADS_PER_BLOCK])
        if args.threads_per_block != recommended_threads:
            console.print(f"[yellow]性能提示: 推荐的线程数为 {recommended_threads}[/yellow]")
        
        # 根据显存估算最大批次大小
        available_memory = device.total_memory() * 0.8
        estimated_memory_per_pwd = 16
        max_batch_size = int(available_memory / estimated_memory_per_pwd)
        
        if args.batch_size > max_batch_size:
            console.print(f"[yellow]警告: 批次大小过大，已自动调整为 {max_batch_size}[/yellow]")
            args.batch_size = max_batch_size
        
        # 准备进度条
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            refresh_per_second=5
        ) as progress:
            task = progress.add_task("[cyan]正在破解密码...", total=None)
            
            start_time = time.time()
            
            # 读取断点
            start_position = None
            if args.resume and os.path.exists(args.checkpoint):
                checkpoint_data = load_checkpoint(args.checkpoint)
                if checkpoint_data:
                    start_position = checkpoint_data.get('position')
                    total_attempts = checkpoint_data.get('attempts', 0)
                    console.print(f"[green]从检查点恢复: 已尝试 {total_attempts} 次密码组合[/green]")
            
            # 使用上下文管理器确保资源清理
            with GPUManager([args.gpu]) as gpu_manager:
                try:
                    cracker = RARCracker(
                        args.rar_file,
                        gpu_manager,
                        mask=args.mask,
                        min_length=args.min_length,
                        max_length=args.max_length,
                        dict_file=args.dict,
                        batch_size=args.batch_size,
                        threads_per_block=args.threads_per_block
                    )
                    
                    # 持续运行直到成功
                    last_update = time.time()
                    for result in cracker.run(start_position):
                        total_attempts += result.get('attempts', 0)
                        
                        # 如果找到密码
                        if result.get('password'):
                            found_password = result['password']
                            
                            # 将密码保存到项目根目录
                            save_found_password(args.rar_file, found_password)
                            break
                        
                        # 保存检查点
                        save_checkpoint(args.checkpoint, {
                            'position': result.get('position'),
                            'attempts': total_attempts
                        })
                        
                        # 更新进度显示
                        current_time = time.time()
                        if current_time - last_update >= args.update_interval:
                            elapsed = current_time - start_time
                            speed = total_attempts / elapsed if elapsed > 0 else 0
                            
                            # 更新进度条描述
                            progress.update(
                                task, 
                                description=f"[cyan]正在破解密码... 速度: {format_speed(speed)}/秒 | 已尝试: {total_attempts:,} 组合[/cyan]"
                            )
                            last_update = current_time
                            
                except Exception as e:
                    console.print(f"[bold red]破解过程中出错: {str(e)}[/bold red]")
                    traceback.print_exc()
            
            # 显示结果
            console.print("\n" + "=" * 60)
            if found_password:
                console.print(f"[bold green]成功找到密码: {found_password}[/bold green]")
                console.print(f"[bold green]密码已保存到项目根目录下的密码文件中[/bold green]")
            else:
                console.print("[bold red]未找到密码，已尝试所有可能组合[/bold red]")
            
            elapsed = time.time() - start_time
            speed = total_attempts / elapsed if elapsed > 0 else 0
            console.print(f"总尝试次数: {total_attempts:,}")
            console.print(f"总耗时: {elapsed:.2f} 秒")
            console.print(f"平均速度: {format_speed(speed)}/秒")
            
    except KeyboardInterrupt:
        console.print("\n[bold red]程序被用户中断[/bold red]")
    except Exception as e:
        console.print(f"[bold red]程序错误: {str(e)}[/bold red]")
        traceback.print_exc()
    finally:
        # 清理所有CUDA资源
        try:
            while True:
                try:
                    ctx = cuda.Context.get_current()
                    if ctx is None:
                        break
                    ctx.pop()
                except cuda.Error:
                    break
        except:
            pass

def save_found_password(rar_file, password):
    """将找到的密码保存到项目根目录"""
    try:
        # 创建文件名，包含RAR文件名和时间戳
        rar_name = os.path.basename(rar_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"password_found_{rar_name}_{timestamp}.txt"
        
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(root_dir, filename)
        
        # 将密码写入文件
        with open(filepath, 'w') as f:
            f.write(f"RAR文件: {rar_file}\n")
            f.write(f"破解时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"密码: {password}\n")
        
        print(f"\n密码已保存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"保存密码时出错: {e}")
        return None

if __name__ == "__main__":
    sys.exit(main()) 