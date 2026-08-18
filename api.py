import asyncio
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from run import run_automation

app = FastAPI(title="Naukri Resume Updater")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/run")
async def run_resume_update():
    try:
        await asyncio.to_thread(run_automation)
        return {
            "status": "success",
            "message": "Resume update automation completed."
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(exc),
            },
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
