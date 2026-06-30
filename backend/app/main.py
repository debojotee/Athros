import os
import uuid
import shutil
import logging
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.services.video_processor import interleave_videos

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="Athros API",
    description="Backend API to interleave two videos at a frame level",
    version="1.0.0"
)

# Standard CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up absolute path variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
UPLOAD_DIR = os.path.join(TEMP_DIR, "uploads")
OUTPUT_DIR = os.path.join(TEMP_DIR, "outputs")

# Ensure temporary files directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# In-memory database for tracking jobs
# Format: { task_id: { "status": "pending|processing|completed|failed", "progress": 0, "error": None, "output_file": None } }
tasks = {}

def process_video_task(task_id: str, path_a: str, path_b: str, out_path: str, chunk_size: int = 6):
    """
    Background worker that invokes the video processor and updates the task status.
    """
    tasks[task_id]["status"] = "processing"
    tasks[task_id]["progress"] = 0
    
    def progress_callback(percentage: int):
        tasks[task_id]["progress"] = percentage

    try:
        interleave_videos(path_a, path_b, out_path, chunk_size=chunk_size, progress_callback=progress_callback)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["output_file"] = out_path
        
        # Clean up raw uploads to save disk space
        if os.path.exists(path_a):
            os.remove(path_a)
        if os.path.exists(path_b):
            os.remove(path_b)
        logger.info(f"Task {task_id} completed successfully.")
    except Exception as e:
        logger.exception(f"Error executing task {task_id}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        
        # Clean up files on error
        if os.path.exists(path_a):
            os.remove(path_a)
        if os.path.exists(path_b):
            os.remove(path_b)

@app.post("/api/upload")
async def upload_videos(
    background_tasks: BackgroundTasks,
    video_a: UploadFile = File(...),
    video_b: UploadFile = File(...),
    interval_frames: int = Form(6)
):
    """
    Uploads video A and video B, creates a background processing task,
    and returns a task ID to track progress.
    """
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    
    ext_a = os.path.splitext(video_a.filename)[1].lower()
    ext_b = os.path.splitext(video_b.filename)[1].lower()
    
    if ext_a not in allowed_extensions or ext_b not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed formats: {', '.join(allowed_extensions)}"
        )

    task_id = str(uuid.uuid4())
    
    path_a = os.path.join(UPLOAD_DIR, f"{task_id}_a{ext_a}")
    path_b = os.path.join(UPLOAD_DIR, f"{task_id}_b{ext_b}")
    out_path = os.path.join(OUTPUT_DIR, f"{task_id}_output.mp4")

    # Save files to temp directory
    try:
        with open(path_a, "wb") as f_a:
            shutil.copyfileobj(video_a.file, f_a)
        with open(path_b, "wb") as f_b:
            shutil.copyfileobj(video_b.file, f_b)
    except Exception as e:
        logger.error(f"Failed writing uploaded files for task {task_id}: {e}")
        if os.path.exists(path_a):
            os.remove(path_a)
        if os.path.exists(path_b):
            os.remove(path_b)
        raise HTTPException(status_code=500, detail="Failed to save uploaded files on server.")

    # Initialize job state
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "error": None,
        "output_file": None
    }

    # Queue background video processing
    background_tasks.add_task(process_video_task, task_id, path_a, path_b, out_path, interval_frames)

    return {"task_id": task_id, "status": "pending"}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """
    Returns the processing status and completion percentage of a task.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks[task_id]
    response = {
        "status": task_info["status"],
        "progress": task_info["progress"],
        "error": task_info["error"]
    }
    
    if task_info["status"] == "completed":
        response["download_url"] = f"/api/download/{task_id}"
        
    return response

@app.get("/api/download/{task_id}")
async def download_video(task_id: str):
    """
    Downloads the resulting processed video file.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_info = tasks[task_id]
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video is not ready yet")
        
    file_path = task_info["output_file"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename="interleaved_output.mp4"
    )

# Mount the static files directory containing HTML/CSS/JS frontend
# Serve index.html as the root fallback
static_dir = os.path.join(BASE_DIR, "app", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning(f"Static directory not found at: {static_dir}. Root path will not serve frontend.")
