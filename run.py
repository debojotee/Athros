import uvicorn
import sys
import os

# Ensure the backend directory is in the path so we can resolve "app" module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

if __name__ == "__main__":
    print("Starting Athros on http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
