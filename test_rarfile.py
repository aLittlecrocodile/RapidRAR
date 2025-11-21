import rarfile
import shutil
import sys

print(f"rarfile version: {rarfile.__version__}")
print(f"UNRAR_TOOL: {rarfile.UNRAR_TOOL}")

# Check if UNRAR_TOOL exists
if shutil.which(rarfile.UNRAR_TOOL):
    print(f"Tool found at: {shutil.which(rarfile.UNRAR_TOOL)}")
else:
    print("Tool NOT found.")
    # Try to find bsdtar
    bsdtar = shutil.which('bsdtar')
    if bsdtar:
        print(f"Found bsdtar at: {bsdtar}")
        rarfile.UNRAR_TOOL = bsdtar
        print("Set UNRAR_TOOL to bsdtar")
    else:
        print("bsdtar NOT found either.")

try:
    # Create a dummy rar file object (won't work without a real file, but checks init)
    # We need a real file to test.
    pass
except Exception as e:
    print(f"Error: {e}")
