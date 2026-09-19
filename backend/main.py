<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.health import router as health_router
from routes.analyze import router as analyze_router
from routes.sessions import router as session_router
from routes.audit import router as audit_router

from websocket.audio import router as websocket_router


app = FastAPI(
    title="EchoShield AI",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(analyze_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "name": "EchoShield AI",
        "status": "running"
=======
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.health import router as health_router
from routes.analyze import router as analyze_router
from routes.sessions import router as session_router

from websocket.audio import router as websocket_router


app = FastAPI(
    title="EchoShield AI",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(analyze_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "name": "EchoShield AI",
        "status": "running"
>>>>>>> 3b89e99 (Integrate W2V2 detection with Android and backend)
    }