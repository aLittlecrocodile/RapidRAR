import logging
import numpy as np
from .base import CrackerBackend

# Try to import GPUManager, but don't fail if pycuda is missing
try:
    from ..gpu_manager import GPUManager
    from ..cuda_kernels import get_kernel_code
    import pycuda.driver as cuda
    HAS_CUDA = True
except ImportError:
    HAS_CUDA = False

class CUDABackend(CrackerBackend):
    """
    CUDA-based backend for NVIDIA GPUs.
    """
    
    def __init__(self, gpu_id=0, threads_per_block=256):
        if not HAS_CUDA:
            raise RuntimeError("CUDA backend requires pycuda and an NVIDIA GPU.")
        self.gpu_id = gpu_id
        self.threads_per_block = threads_per_block
        self.gpu_manager = None
        self.check_kernel = None
        self.rar_header = None
        
    def init(self):
        """Initialize CUDA context and kernels."""
        self.gpu_manager = GPUManager([self.gpu_id])
        # We need to compile kernels. 
        # Note: GPUManager._compile_kernels is internal, but we can use it or do it manually.
        # For simplicity, let's reuse GPUManager's context but compile our specific kernel here
        # or rely on what we had.
        
        # Actually, let's just use the raw pycuda logic similar to the original cracker.py
        # to avoid complex dependency on the old GPUManager if we want to refactor it out later.
        # But for now, reusing GPUManager is easier.
        
        self.gpu_manager._compile_kernels(self.gpu_id)
        self.check_kernel = self.gpu_manager.functions[self.gpu_id]['check_rar_password']
        
    def set_rar_header(self, rar_header):
        """Set the RAR header data for checking."""
        self.rar_header = rar_header
        
    def check_passwords(self, passwords, rar_file):
        """
        Check a batch of passwords on GPU.
        """
        if not passwords:
            return None
            
        # Prepare data
        password_data = ''.join(passwords)
        password_lengths = [len(p) for p in passwords]
        num_passwords = len(passwords)
        
        # Allocate memory
        passwords_gpu = self.gpu_manager.allocate_memory(self.gpu_id, len(password_data))
        lengths_gpu = self.gpu_manager.allocate_memory(self.gpu_id, len(password_lengths) * 4)
        results_gpu = self.gpu_manager.allocate_memory(self.gpu_id, num_passwords * 4)
        
        # We also need header gpu if we haven't allocated it yet, or allocate per batch
        # For simplicity, allocate per batch
        header_gpu = self.gpu_manager.allocate_memory(self.gpu_id, len(self.rar_header))
        
        try:
            # Copy data
            self.gpu_manager.copy_to_device(self.gpu_id, np.array([ord(c) for c in password_data], dtype=np.uint8), passwords_gpu)
            self.gpu_manager.copy_to_device(self.gpu_id, np.array(password_lengths, dtype=np.int32), lengths_gpu)
            self.gpu_manager.copy_to_device(self.gpu_id, np.array([b for b in self.rar_header], dtype=np.uint8), header_gpu)
            
            # Execute kernel
            self.gpu_manager.execute_kernel(
                self.gpu_id, 'check_rar_password',
                passwords_gpu, lengths_gpu, np.int32(num_passwords),
                header_gpu, np.int32(len(self.rar_header)),
                results_gpu,
                num_items=num_passwords
            )
            
            # Get results
            results = np.zeros(num_passwords, dtype=np.int32)
            self.gpu_manager.copy_from_device(self.gpu_id, results_gpu, results)
            
            # Check results
            for i, res in enumerate(results):
                if res == 1:
                    return passwords[i]
                    
        finally:
            # Free memory (pycuda handles this via refcounting usually, but explicit free is good if using raw pointers)
            # GPUManager doesn't expose free easily, but pycuda objects do.
            pass
            
        return None
        
    def cleanup(self):
        if self.gpu_manager:
            self.gpu_manager.cleanup()
