"""
FastAPI Main Application - Basis Version
RA Autohaus Tracker MVP
"""

from fastapi import FastAPI

app = FastAPI(
    title="RA Autohaus Tracker",
    version="1.0.0-alpha"
)

@app.get("/")
def root():
    return {"message": "RA Autohaus Tracker MVP läuft!"}

@app.get("/health")  
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
