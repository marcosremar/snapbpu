import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Dumont Cloud Live Docs CMS", docs_url=None, redoc_url=None)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "marketing_doc.html")

def get_menu_structure(path):
    """
    Recursively scans the directory to build the menu structure.
    Returns a list of dicts: {name: str, type: 'file'|'dir', path: str, children: []}
    """
    items = []
    if not os.path.exists(path):
        return items

    for entry in sorted(os.listdir(path)):
        if entry.startswith('.'):
            continue
            
        full_path = os.path.join(path, entry)
        relative_path = os.path.relpath(full_path, CONTENT_DIR)
        
        if os.path.isdir(full_path):
            items.append({
                "name": entry,
                "type": "dir",
                "path": relative_path,
                "children": get_menu_structure(full_path)
            })
        elif entry.endswith(".md"):
            # Remove extension for display, keep relative path for ID
            display_name = os.path.splitext(entry)[0].replace('_', ' ')
            items.append({
                "name": display_name,
                "type": "file",
                "path": relative_path,  # e.g., "Strategy/Marketing_Plan.md"
                "id": relative_path     # used for fetching content
            })
            
    return items

@app.get("/admin/doc/live", response_class=HTMLResponse)
async def serve_app():
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Template not found. Please create Live-Doc/templates/marketing_doc.html</h1>", 404

@app.get("/api/menu")
async def get_menu():
    """Returns the directory structure as JSON for the sidebar"""
    return {"menu": get_menu_structure(CONTENT_DIR)}

@app.get("/api/content/{path:path}")
async def get_content(path: str):
    """Fetches key content by relative path"""
    # Security: Prevent directory traversal
    safe_path = os.path.normpath(os.path.join(CONTENT_DIR, path))
    if not safe_path.startswith(CONTENT_DIR):
         raise HTTPException(status_code=403, detail="Access denied")
         
    if os.path.exists(safe_path) and os.path.isfile(safe_path):
        with open(safe_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
            
    raise HTTPException(status_code=404, detail="Document not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")
