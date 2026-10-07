from fastapi import FastAPI

app = FastAPI(title="Bulk Certificate Generator")


@app.get("/health")
def health():
    return {"status": "ok"}