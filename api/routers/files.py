# from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
# from pathlib import Path
# import os
# import uuid

# router = APIRouter()

# SHARED_DATA_PATH = Path("/app/data")
# SHARED_DATA_PATH.mkdir(exist_ok=True)

# @router.post("/upload")
# async def upload_file(file: UploadFile = File(...)):

#     allowed_extensions = {'.csv', '.xlsx', '.json', '.txt', '.parquet'}
#     file_ext = Path(file.filename).suffix.lower()

#     if file_ext not in allowed_extensions:
#         raise HTTPException(400, f"File type {file_ext} not allowed")

#     file_path = SHARED_DATA_PATH / file.filename

#     content = await file.read()
#     with open(file_path, "wb") as f:
#         f.write(content)
    
#     return {
#         "filename": file.filename,
#         "size": len(content),
#         "path": str(file_path)
#     }

# @router.get("/files")
# async def list_files():
#     """List all uploaded files"""
#     files = []
#     for file_path in SHARED_DATA_PATH.iterdir():
#         if file_path.is_file():
#             files.append({
#                 "filename": file_path.name,
#                 "size": file_path.stat().st_size,
#                 "modified": file_path.stat().st_mtime
#             })
#     return {"files": files}
