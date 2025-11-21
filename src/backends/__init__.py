from .cpu import CPUBackend

def get_backend(backend_name='auto', **kwargs):
    """
    Factory to get the appropriate backend.
    """
    if backend_name == 'cuda':
        try:
            from .cuda import CUDABackend
            return CUDABackend(**kwargs)
        except (ImportError, RuntimeError) as e:
            raise RuntimeError(f"Could not initialize CUDA backend: {e}")
            
    elif backend_name == 'cpu':
        return CPUBackend(**kwargs)
        
    elif backend_name == 'auto':
        # Try CUDA first
        try:
            from .cuda import CUDABackend, HAS_CUDA
            if HAS_CUDA:
                return CUDABackend(**kwargs)
        except:
            pass
            
        # Fallback to CPU
        return CPUBackend(**kwargs)
        
    else:
        raise ValueError(f"Unknown backend: {backend_name}")
