import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.core.config import TRACE_ID_HEADER_NAME, ctx_trace_id, get_request_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get(TRACE_ID_HEADER_NAME, str(uuid.uuid4()))
        t_token = ctx_trace_id.set(trace_id)

        start_time = time.time()
        try:
            logger = get_request_logger()
            request.state.trace_id = trace_id

            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8", errors="replace")

            logger.info(
                f"Incoming request: {request.method} {request.url.path} "
                f"query={dict(request.query_params)} "
                f"client={request.client.host if request.client else 'unknown'} "
                f"user-agent={request.headers.get('user-agent')} "
                f"body_length={len(body_str)}"
            )

            response = await call_next(request)

            duration = (time.time() - start_time) * 1000
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"status_code={response.status_code} "
                f"duration={duration:.2f}ms "
            )
            response.headers[TRACE_ID_HEADER_NAME] = trace_id
            return response
        except Exception as e:
            get_request_logger().exception(
                f"Unhandled error within request execution flow: {e}"
            )
            raise
        finally:
            ctx_trace_id.reset(t_token)
