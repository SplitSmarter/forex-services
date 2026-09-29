from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import TRACE_ID_HEADER_NAME
from src.exception_handler import register_exception_handlers
from src.lifespan import lifespan
from src.middlewares.LoggingMiddleware import LoggingMiddleware
from src.routes.forex.forex_route import router as forex_router

app = FastAPI(title="Forex Service", lifespan=lifespan)

app.include_router(forex_router)

custom_headers = [
    TRACE_ID_HEADER_NAME,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "DELETE", "PUT", "UPDATE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=custom_headers,
)
app.add_middleware(LoggingMiddleware)

register_exception_handlers(app)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
