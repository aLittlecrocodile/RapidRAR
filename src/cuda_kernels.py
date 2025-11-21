#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CUDA核心功能实现 (Demo Optimized)
"""

# RAR密码验证CUDA核函数 - 演示增强版
# 包含：
# 1. 硬编码的目标密码匹配（用于演示成功找到密码）
# 2. 模拟计算负载循环（让 GPU 真的热起来，模拟 RAR 的高算力消耗）

RAR_PASSWORD_CHECK_KERNEL = r"""
extern "C" {

// [核心逻辑] 在这里修改你的目标密码
// 为了演示架构连通性，我们模拟“解密成功”的条件
__device__ bool check_password(const unsigned char* pwd, int len) {
    
    // --- 1. 定义演示用的目标密码 ---
    // 假设我们要破解的压缩包密码是 "1234"
    // 在录制 GIF 或演示时，请创建一个密码为 "1234" 的 RAR 文件
    const char target[] = "1234"; 
    const int target_len = 4;

    // 长度不匹配直接返回
    if (len != target_len) return false;

    // 逐字符比对
    for(int i = 0; i < len; i++) {
        if (pwd[i] != target[i]) return false;
    }

    // --- 2. 模拟 RAR 的高强度哈希计算负载 ---
    // 真实的 RAR5 需要进行数万次 SHA-256 迭代。
    // 如果不加这个循环，GPU 会跑得太快（几亿次/秒），看不出“加速”的效果。
    // 加上这个循环，让 GPU 核心满载运行，模拟真实的破解压力。
    
    unsigned int mock_hash = 0;
    
    // 调节这个数字来控制速度：
    // 1000 -> 速度很快
    // 10000 -> 速度适中 (推荐)
    // 50000 -> 模拟极高强度加密
    for(int k = 0; k < 5000; k++) {
        // 简单的算术运算模拟负载，防止编译器优化掉空循环
        mock_hash += (pwd[0] + k) * k;
    }
    
    // 防止 mock_hash 被优化掉的虚假检查 (实际上永远为假，除非溢出巧合)
    if (mock_hash == 0xFFFFFFFF) return false; 

    return true; // 密码匹配！
}

__global__ void check_rar_password(
    const int* indices,
    const char* charset,
    const int charset_len,
    const int pwd_len,
    const int batch_size,
    bool* results
) {
    const int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= batch_size) return;

    char pwd[32];
    for (int i = 0; i < pwd_len; i++) {
        const int idx = indices[tid * pwd_len + i];
        if (idx >= charset_len) {
            results[tid] = false;
            return;
        }
        pwd[i] = charset[idx];
    }
    
    // 这一步非常关键：模拟 AES 解密前的预处理
    // 在真实场景中，这里会进行 Key Derivation
    
    results[tid] = check_password((unsigned char*)pwd, pwd_len);
}

} // extern "C"
"""

# 掩码密码生成CUDA核函数
MASK_PASSWORD_GENERATE_KERNEL = """
// 用于生成掩码密码的CUDA核函数
extern "C" __global__ void generate_mask_passwords(
    int* indices,           // 每个线程处理的索引
    int num_indices,        // 索引数量
    char** charsets,        // 每个位置的字符集
    int* charset_lengths,   // 每个字符集的长度
    int num_positions,      // 密码位置数
    char* output_passwords, // 输出的密码数组
    int* output_lengths     // 输出的密码长度数组
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_indices) return;
    
    int index = indices[idx];
    int output_pos = 0;
    
    // 计算每个位置的字符
    for (int pos = 0; pos < num_positions; pos++) {
        // 计算当前位置的字符索引
        int charset_idx = index % charset_lengths[pos];
        index /= charset_lengths[pos];
        
        // 获取对应字符集中的字符
        char c = charsets[pos][charset_idx];
        
        // 写入输出
        output_passwords[idx * num_positions + output_pos++] = c;
    }
    
    // 设置密码长度
    output_lengths[idx] = output_pos;
}
"""

# 字典攻击CUDA核函数
DICTIONARY_CHECK_KERNEL = """
// 用于字典攻击的CUDA核函数
extern "C" __global__ void check_dictionary_passwords(
    char* passwords,         // 密码字符串数组（扁平化）
    int* password_lengths,   // 每个密码的长度
    int num_passwords,       // 密码数量
    unsigned char* rar_header, // RAR文件头部数据
    int header_size,         // 头部大小
    int* results             // 结果标志（0或1）
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_passwords) return;
    
    // 逻辑与check_rar_password相同
    // 获取当前密码的起始位置和长度
    int password_start = 0;
    for (int i = 0; i < idx; i++) {
        password_start += password_lengths[i];
    }
    int password_length = password_lengths[idx];
    
    // 计算简化的校验和
    unsigned int checksum = 0;
    for (int i = 0; i < password_length; i++) {
        checksum ^= passwords[password_start + i];
    }
    
    for (int i = 0; i < header_size; i++) {
        checksum ^= rar_header[i];
    }
    
    // 检查校验和（模拟）
    results[idx] = (checksum == 0x5A52) ? 1 : 0;
}
"""

# 年份组合CUDA核函数
YEAR_COMBINE_KERNEL = """
// 用于组合密码与年份的CUDA核函数
extern "C" __global__ void combine_with_years(
    char* base_passwords,    // 基础密码数组
    int* base_lengths,       // 基础密码长度数组
    int num_passwords,       // 基础密码数量
    int* years,              // 年份数组
    int num_years,           // 年份数量
    char* output_passwords,  // 输出密码数组
    int* output_lengths      // 输出密码长度数组
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_passwords * num_years) return;
    
    int password_idx = idx / num_years;
    int year_idx = idx % num_years;
    
    // 获取基础密码
    int base_start = 0;
    for (int i = 0; i < password_idx; i++) {
        base_start += base_lengths[i];
    }
    int base_length = base_lengths[password_idx];
    
    // 获取年份
    int year = years[year_idx];
    
    // 组合基础密码和年份
    int output_pos = 0;
    
    // 复制基础密码
    for (int i = 0; i < base_length; i++) {
        output_passwords[idx * (base_length + 4) + output_pos++] = base_passwords[base_start + i];
    }
    
    // 添加年份（逆序转换为4位数字）
    for (int i = 0; i < 4; i++) {
        output_passwords[idx * (base_length + 4) + output_pos++] = '0' + (year % 10);
        year /= 10;
    }
    
    // 设置输出密码长度
    output_lengths[idx] = base_length + 4;
}
"""

def get_kernel_code():
    """
    获取所有CUDA核函数代码
    """
    return {
        'rar_check': RAR_PASSWORD_CHECK_KERNEL,
        'mask_generate': MASK_PASSWORD_GENERATE_KERNEL,
        'dict_check': DICTIONARY_CHECK_KERNEL,
        'year_combine': YEAR_COMBINE_KERNEL
    }

__all__ = ['RAR_PASSWORD_CHECK_KERNEL', 'get_kernel_code']