import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Security, Depends
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os

# Import internal modules
# Adjust import path if necessary based on where this file is placed relative to src/
# If src/api.py, then:
from src.cracker import RARCracker
from src.config import DEFAULT_CHARSET

# API Security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """Very simple API Key validation. In production, use database or Vault."""
    expected_key = os.getenv("RAPIDRAR_API_KEY", "dev-secret")
    if api_key_header == expected_key:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


# FastAPI app
app = FastAPI(title="RapidRAR API", description="High-performance RAR password recovery API")

class CrackResponse(BaseModel):
    status: str
    password: Optional[str] = None
    attempts: int
    time_taken: float
    message: str

@app.post("/crack", response_model=CrackResponse)
async def crack_archive(
    file: UploadFile = File(...),
    mask: Optional[str] = Form(None),
    min_length: int = Form(1),
    max_length: int = Form(4), # Default small for quick API tests
    use_digits: bool = Form(False),
    use_lowercase: bool = Form(False),
    use_uppercase: bool = Form(False),
    use_special: bool = Form(False),
    backend: str = Form("auto"),
    api_key: str = Depends(get_api_key)
):
    # Create a temporary directory to store the uploaded file
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, file.filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determine charset
        charset = ""
        if use_lowercase: charset += "abcdefghijklmnopqrstuvwxyz"
        if use_uppercase: charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if use_digits: charset += "0123456789"
        if use_special: charset += "!@#$%^&*()" # Simplified special chars
        
        if not charset and not mask:
            charset = DEFAULT_CHARSET

        try:
            # Initialize Cracker
            # Note: Assuming RARCracker is designed to be blocking. 
            # In a real prod env, this should be a background task (Celery/RQ).
            # For this interview task, synchronous execution is acceptable but we warn about timeout.
            
            cracker = RARCracker(
                rar_file=file_path,
                mask=mask,
                min_length=min_length,
                max_length=max_length,
                backend=backend,
                charset=charset if not mask else None
            )
            
            # Run cracker
            # We need to capture the generator output
            found_password = None
            total_attempts = 0
            
            import time
            start_time = time.time()
            
            for result in cracker.run():
                total_attempts += result.get('attempts', 0)
                if result.get('password'):
                    found_password = result['password']
                    break
            
            elapsed = time.time() - start_time
            
            if found_password:
                return JSONResponse({
                    "status": "success",
                    "password": found_password,
                    "attempts": total_attempts,
                    "time_taken": elapsed,
                    "message": "Password found successfully"
                })
            else:
                 return JSONResponse({
                    "status": "failed",
                    "password": None,
                    "attempts": total_attempts,
                    "time_taken": elapsed,
                    "message": "Password not found within search space"
                })

        except Exception as e:
            return JSONResponse({
                "status": "error",
                "password": None,
                "attempts": 0,
                "time_taken": 0,
                "message": str(e)
            }, status_code=500)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
