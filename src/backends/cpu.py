import os
import concurrent.futures
import rarfile
from .base import CrackerBackend

import zipfile

def check_password_worker(file_path, password):
    """
    Worker function to check a single password.
    Must be at module level for multiprocessing pickling.
    """
    is_zip = file_path.lower().endswith('.zip')
    
    if is_zip:
        try:
            zf = zipfile.ZipFile(file_path)
            # Try to open the first encrypted file
            for zinfo in zf.infolist():
                if zinfo.flag_bits & 0x1:
                    with zf.open(zinfo, pwd=password.encode('utf-8')) as f:
                        f.read(1)
                    return password
            return None
        except (RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile):
            # RuntimeError is raised by zipfile for bad password
            return None
        except Exception:
            return None
    else:
        try:
            rf = rarfile.RarFile(file_path)
            # Try to open the first file in the archive
            # This is usually faster than extractall
            for f in rf.infolist():
                if f.isdir():
                    continue
                with rf.open(f, pwd=password) as _:
                    # If we can read one byte, the password is likely correct
                    _.read(1)
                    return password
            return None
        except (rarfile.PasswordRequired, rarfile.BadRarFile, rarfile.RarCRCError):
            return None
        except Exception:
            return None

class CPUBackend(CrackerBackend):
    """
    CPU-based backend using multiprocessing.
    """
    
    def __init__(self, num_workers=None, **kwargs):
        self.num_workers = num_workers or os.cpu_count()
        self.pool = None
        
    def init(self):
        """Initialize the process pool."""
        # We create the pool lazily or here
        pass
        
    def check_passwords(self, passwords, rar_file):
        """
        Check a batch of passwords using multiprocessing.
        """
        if not self.pool:
            self.pool = concurrent.futures.ProcessPoolExecutor(max_workers=self.num_workers)
            
        futures = []
        for pwd in passwords:
            futures.append(self.pool.submit(check_password_worker, rar_file, pwd))
            
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                # Found a password! Cancel other futures if possible (though hard with processes)
                # and return immediately
                return result
                
        return None
        
    def cleanup(self):
        """Shutdown the pool."""
        if self.pool:
            self.pool.shutdown()
            self.pool = None
