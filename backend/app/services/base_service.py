import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable, Any
from functools import wraps

from app.schemas.internal import AnalysisContext, ServiceResult


class BaseService(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def check(self, ctx: AnalysisContext) -> ServiceResult:
        pass


def safe_execute(timeout_seconds: float = 5.0):
    """
    Decorator to execute a service's check method with timeout and exception handling.
    Returns a ServiceResult with status="error" if an exception or timeout occurs.
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(self: BaseService, ctx: AnalysisContext, *args, **kwargs) -> ServiceResult:
            start_time = time.monotonic()
            try:
                # Use asyncio.wait_for to enforce timeout
                result = await asyncio.wait_for(
                    func(self, ctx, *args, **kwargs),
                    timeout=timeout_seconds
                )
                
                # Make sure duration_ms is correctly populated if not already set (or set it here)
                end_time = time.monotonic()
                if isinstance(result, ServiceResult) and result.duration_ms == 0:
                     result.duration_ms = int((end_time - start_time) * 1000)
                     
                return result
            except asyncio.TimeoutError:
                end_time = time.monotonic()
                duration_ms = int((end_time - start_time) * 1000)
                return ServiceResult(
                    service=self.name,
                    status="error",
                    error="Timeout",
                    duration_ms=duration_ms
                )
            except Exception as e:
                end_time = time.monotonic()
                duration_ms = int((end_time - start_time) * 1000)
                return ServiceResult(
                    service=self.name,
                    status="error",
                    error=str(e),
                    duration_ms=duration_ms
                )
        return wrapper
    return decorator
