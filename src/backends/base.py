from abc import ABC, abstractmethod

class CrackerBackend(ABC):
    """
    Abstract base class for password cracking backends.
    """
    
    @abstractmethod
    def init(self):
        """Initialize the backend resources."""
        pass
        
    @abstractmethod
    def check_passwords(self, passwords, rar_file):
        """
        Check a batch of passwords against the RAR file.
        
        Args:
            passwords (list): List of passwords to check.
            rar_file (str): Path to the RAR file.
            
        Returns:
            str or None: The found password, or None if not found in this batch.
        """
        pass
        
    @abstractmethod
    def cleanup(self):
        """Clean up resources."""
        pass
