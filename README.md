# RapidRAR: 高性能GPU驱动的RAR密码恢复工具

<div align="center">
  <img src="https://img.shields.io/badge/CUDA-Powered-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="CUDA Powered">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <br>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" alt="Platform">
</div>

## 📖 概述

RapidRAR是一个专为密码恢复设计的高性能工具，利用GPU并行计算能力实现RAR压缩文件的快速密码破解。无论是误存的个人压缩文件，还是需要进行安全测试的企业环境，RapidRAR都能提供卓越的性能和灵活的攻击策略。

特点：
- ⚡ **CUDA加速**：利用NVIDIA GPU的并行计算能力，比CPU快数十倍
- 🔄 **断点续传**：支持中断后继续，无需重新开始
- 🎮 **多种攻击模式**：支持掩码攻击、字典攻击和暴力破解
- 📊 **实时进度**：直观显示破解速度和进度
- 🧩 **灵活配置**：根据硬件性能和需求定制参数

> ⚠️ **免责声明**：RapidRAR仅供合法恢复自己文件密码使用。请勿用于未经授权的解密行为。

## 🛠️ 安装

### 前提条件
- NVIDIA GPU (支持CUDA)
- CUDA Toolkit 12.0+
- Python 3.8+

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/rapidrar.git
cd rapidrar
```

2. **安装依赖**
```bash
# 推荐使用虚拟环境
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

3. **安装UnRAR**

- **Ubuntu/Debian**:
```bash
sudo apt-get install unrar
```

- **RHEL/CentOS**:
```bash
sudo yum install unrar
```

- **macOS**:
```bash
brew install unrar
```

- **Windows**: 
下载并安装[WinRAR](https://www.win-rar.com/)

## 🚀 使用方法

### 基本用法

```bash
python main.py --rar_file <RAR文件路径> --mask <密码掩码> --gpu <GPU ID>
```

### 示例

#### 掩码攻击 (最常用)
```bash
# 试破解8位密码，前4位是任意字符，后4位是数字
python main.py --rar_file example.rar --mask "?a?a?a?a?d?d?d?d" --gpu 0

# 试破解6位纯数字密码
python main.py --rar_file example.rar --mask "?d?d?d?d?d?d" --gpu 0

# 试破解密码格式为"admin"加3位数字
python main.py --rar_file example.rar --mask "admin?d?d?d" --gpu 0
```

#### 字典攻击
```bash
python main.py --rar_file example.rar --dict wordlist.txt --gpu 0
```

#### 暴力破解
```bash
python main.py --rar_file example.rar --min_length 6 --max_length 8 --gpu 0
```

#### 性能优化
```bash
python main.py --rar_file example.rar --mask "?a?a?a?a?d?d?d?d" --gpu 0 --threads_per_block 1024 --batch_size 20000000 --concurrent_batches 3
```

### 完整参数列表

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--rar_file` | - | RAR文件路径（必填） |
| `--mask` | None | 密码掩码（如 ?a?a?a?a?d?d?d?d） |
| `--dict` | None | 字典文件路径 |
| `--min_length` | 8 | 最小密码长度 |
| `--max_length` | 12 | 最大密码长度 |
| `--gpu` | 0 | 使用的GPU ID |
| `--threads_per_block` | 256 | CUDA每个块的线程数 |
| `--batch_size` | 10000000 | 每批处理的密码数量 |
| `--concurrent_batches` | 2 | 并行批次数 |
| `--checkpoint` | checkpoint.json | 检查点文件路径 |
| `--resume` | False | 从检查点恢复 |
| `--update_interval` | 1.0 | 进度更新间隔（秒） |

### 掩码符号说明

| 符号 | 描述 | 示例 |
|------|------|------|
| `?a` | 所有字符 | a-z, A-Z, 0-9, 特殊字符 |
| `?l` | 小写字母 | a-z |
| `?u` | 大写字母 | A-Z |
| `?d` | 数字 | 0-9 |
| `?s` | 特殊字符 | !@#$%^&*()等 |

## 💡 破解策略

### 高效破解技巧

1. **从简单常见密码开始**
   - 尝试6-8位纯数字: `--mask "?d?d?d?d?d?d"`
   - 常见组合如手机号后6位、生日等: `--mask "?d?d?d?d?d?d"`

2. **尝试常见密码模式**
   - 小写字母+数字: `--mask "?l?l?l?l?d?d?d?d"`
   - 首字母大写+小写字母+数字: `--mask "?u?l?l?l?l?d?d?d"`

3. **使用已知信息**
   - 已知用户名或常用ID加数字: `--mask "admin?d?d?d?d"`
   - 公司名字缩写+年份: `--mask "company2024"`

4. **常见单词组合**
   - 常见单词加数字: `--mask "password?d?d?d?d"`
   - 名字加生日: `--mask "name?d?d?d?d"`

5. **逐步提高复杂度**
   - 从简单到复杂，避免不必要的计算

## 🔧 进阶配置

### GPU性能优化

为RTX 3050/3060/3070/3080/3090系列显卡推荐配置:
```bash
--threads_per_block 1024 --batch_size 20000000 --concurrent_batches 3
```

为GTX 1650/1660系列显卡推荐配置:
```bash
--threads_per_block 768 --batch_size 10000000 --concurrent_batches 2
```

### 自定义字符集

在密码中包含特定字符：
```bash
--charset "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
```

## 📊 性能对比

| GPU型号 | 密码复杂度 | 处理速度(密码/秒) |
|---------|-----------|------------------|
| RTX 3090 | 8位混合字符 | ~2,500,000,000 |
| RTX 3080 | 8位混合字符 | ~1,800,000,000 |
| RTX 3070 | 8位混合字符 | ~1,200,000,000 |
| RTX 3060 | 8位混合字符 | ~800,000,000 |
| RTX 3050 | 8位混合字符 | ~500,000,000 |
| CPU(8核) | 8位混合字符 | ~10,000,000 |

> 注：实际速度取决于具体硬件配置和参数设置

## 📁 项目结构

```
RapidRAR/
├── main.py              # 程序入口
├── requirements.txt     # 依赖列表
├── README.md            # 项目说明
└── src/
    ├── __init__.py      # 包初始化
    ├── cracker.py       # 核心破解逻辑
    ├── cuda_kernels.py  # CUDA核函数
    ├── gpu_manager.py   # GPU资源管理
    ├── config.py        # 配置常量
    └── utils.py         # 通用工具函数
```

## 🤝 贡献指南

欢迎为RapidRAR做出贡献！以下是参与方式：

1. Fork本仓库
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add some amazing feature'`
4. 推送到分支: `git push origin feature/amazing-feature`
5. 提交Pull Request

## 📜 许可证

本项目采用MIT许可证 - 详情见[LICENSE](LICENSE)文件

## 🌟 致谢

- NVIDIA - 提供CUDA技术
- PyCUDA团队 - 提供Python CUDA绑定
- rarfile - 提供RAR文件处理库

## 📬 联系方式

有问题或建议？请在GitHub Issue中提出，或联系：

- Email: your.email@example.com
- GitHub: [Your GitHub Profile](https://github.com/yourusername)

---

<div align="center">
  <p>⭐ 如果这个项目对你有帮助，别忘了Star! ⭐</p>
  <p>RapidRAR - 超越极限，加速恢复</p>
</div>
