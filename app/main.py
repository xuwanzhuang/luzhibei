from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .detector import Detector, ModelNotLoadedError
from .routers import image, video
from .tasks import TaskRegistry
from .validators import ValidationError

app = FastAPI(title="火点/烟雾目标检测")


@app.on_event("startup")
async def _startup():
    detector = Detector()
    detector.load()
    app.state.detector = detector
    app.state.registry = TaskRegistry()


@app.exception_handler(ValidationError)
async def _validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=exc.code, content={"code": exc.code, "message": exc.message})


@app.exception_handler(ModelNotLoadedError)
async def _model_handler(request: Request, exc: ModelNotLoadedError):
    return JSONResponse(status_code=503, content={"code": 503, "message": str(exc)})


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"code": 500, "message": "服务器处理异常，请重试"}
    )


@app.get("/api/health")
async def health():
    detector = getattr(app.state, "detector", None)
    return {
        "model_ready": bool(detector and detector.ready),
        "model_error": getattr(detector, "load_error", None),
        "class_names": getattr(detector, "class_names", {}),
    }


@app.get("/")
async def index():
    return FileResponse(config.STATIC_DIR / "index.html")


app.include_router(image.router)
app.include_router(video.router)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
