from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import shutil
import os
import uuid
import asyncio
from typing import Optional
from src.cracker import RARCracker
from src.backends import get_backend
from src.utils import parse_mask

app = FastAPI(title="RapidRAR API", description="High-Performance Distributed RAR Cracker API")

# Ensure temp directory exists
TEMP_DIR = "/tmp/rapidrar_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

class CrackRequest(BaseModel):
    mask: str = "?d?d?d?d"
    backend: str = "cpu"
    concurrent_batches: int = 4

@app.post("/crack")
async def crack_archive(
    file: UploadFile = File(...),
    mask: str = Form("?d?d?d?d"),
    backend: str = Form("cpu"),
    concurrent_batches: int = Form(4)
):
    """
    Upload a RAR file and attempt to crack it using the specified mask and backend.
    """
    request_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TEMP_DIR, f"{request_id}_{file.filename}")
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"[{request_id}] Received file: {file.filename}, Mask: {mask}, Backend: {backend}")

        # Initialize Cracker
        # We run this in a thread pool to avoid blocking the async loop
        result = await asyncio.to_thread(
            run_cracker, 
            temp_file_path, 
            mask, 
            backend, 
            concurrent_batches
        )
        
        if result:
            return {"status": "success", "password": result}
        else:
            return {"status": "failure", "message": "Password not found"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def run_cracker(rar_file_path, mask, backend_name, concurrent_batches):
    """
    Synchronous wrapper to run the cracker logic
    """
    try:
        # Initialize backend
        backend = get_backend(backend_name)
        backend.init()
        
        # Parse mask info just to get length range (simplified logic here)
        # In a real app we might want to pass more granular params
        mask_info = parse_mask(mask)
        min_len = len(mask_info)
        max_len = len(mask_info)

        cracker = RARCracker(
            rar_file=rar_file_path,
            backend=backend,
            min_length=min_len,
            max_length=max_len,
            mask=mask,
            batch_size=1000, # default
            concurrent_batches=concurrent_batches
        )
        
        start_time = asyncio.get_event_loop().time()
        password = cracker.crack()
        
        backend.cleanup()
        return password
        
    except Exception as e:
        print(f"Cracker error: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
