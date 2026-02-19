# Performance Optimization for MCP SDK

This reference covers strategies and best practices for optimizing MCP server and client performance.

## Connection Management

### Connection Pooling
```python
import asyncio
from typing import List, Optional
from mcp.client import Client
from mcp.transport import Transport

class ConnectionPool:
    def __init__(self, create_transport_func, max_connections: int = 10):
        self.create_transport_func = create_transport_func
        self.max_connections = max_connections
        self.pool: List[Client] = []
        self.active_connections: List[Client] = []
        self.semaphore = asyncio.Semaphore(max_connections)

    async def get_connection(self) -> Client:
        """Get a connection from the pool"""
        await self.semaphore.acquire()

        if self.pool:
            client = self.pool.pop()
        else:
            # Create new connection
            transport = self.create_transport_func()
            client = Client(transport)
            await client.connect()

        self.active_connections.append(client)
        return client

    async def return_connection(self, client: Client):
        """Return a connection to the pool"""
        if client in self.active_connections:
            self.active_connections.remove(client)

        if len(self.pool) < self.max_connections:
            self.pool.append(client)
        else:
            # Close excess connections
            await client.disconnect()

        self.semaphore.release()

    async def close_all(self):
        """Close all connections in the pool"""
        for client in self.pool + self.active_connections:
            try:
                await client.disconnect()
            except:
                pass  # Ignore errors during shutdown

# Usage example
# async def use_connection_pool():
#     def create_transport():
#         # Return appropriate transport
#         pass
#
#     pool = ConnectionPool(create_transport, max_connections=5)
#
#     async def make_request():
#         client = await pool.get_connection()
#         try:
#             result = await client.call_tool("some_tool", {})
#             return result
#         finally:
#             await pool.return_connection(client)
```

### Efficient Transport Usage
```python
from mcp.transport import Transport
import asyncio
from typing import Dict, Any

class EfficientTransportManager:
    def __init__(self):
        self.active_transports: Dict[str, Transport] = {}
        self.transport_locks: Dict[str, asyncio.Lock] = {}

    async def get_or_create_transport(self, identifier: str, create_func) -> Transport:
        """Get or create a transport with thread safety"""
        if identifier not in self.transport_locks:
            self.transport_locks[identifier] = asyncio.Lock()

        async with self.transport_locks[identifier]:
            if identifier not in self.active_transports:
                transport = create_func()
                self.active_transports[identifier] = transport

            return self.active_transports[identifier]

    async def close_transport(self, identifier: str):
        """Close and remove a transport"""
        if identifier in self.active_transports:
            transport = self.active_transports[identifier]
            try:
                await transport.close()
            except:
                pass  # Ignore errors during transport closure
            finally:
                del self.active_transports[identifier]
```

## Caching Strategies

### Resource Caching
```python
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

class ResourceCache:
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self.lock = asyncio.Lock()
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if not expired"""
        async with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    return value
                else:
                    # Remove expired entry
                    del self.cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in cache with TTL"""
        ttl = ttl or self.default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)

        async with self.lock:
            self.cache[key] = (value, expiry)

    async def invalidate(self, key: str):
        """Invalidate a specific cache entry"""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]

    async def clear_expired(self):
        """Remove all expired entries"""
        async with self.lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, expiry) in self.cache.items()
                if now >= expiry
            ]

            for key in expired_keys:
                del self.cache[key]
```

### Server-Side Caching
```python
from mcp.server import Server
from mcp.types import ResourceTemplate
import hashlib

class CachedResourceProvider:
    def __init__(self, server: Server, cache_ttl: int = 300):
        self.server = server
        self.cache = ResourceCache(default_ttl=cache_ttl)

    def register_cached_resource(self, template: ResourceTemplate, ttl: int = None):
        """Register a resource with automatic caching"""
        def decorator(func):
            @self.server.handler.register_resource_template(template)
            async def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                cache_key = f"{template.name}:{hash(str(args) + str(kwargs))}"

                # Try to get from cache first
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Call the function and cache the result
                result = await func(*args, **kwargs)
                await self.cache.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator

# Example usage
# provider = CachedResourceProvider(server)
#
# @provider.register_cached_resource(
#     ResourceTemplate(
#         uriTemplate="urn:expensive:calculation",
#         name="expensive-calculation",
#         description="Expensive calculation with caching"
#     ),
#     ttl=600  # 10 minute cache
# )
# async def expensive_calculation_handler(x: int, y: int):
#     # Simulate expensive operation
#     await asyncio.sleep(1)
#     return {"result": x * y, "calculated_at": datetime.now().isoformat()}
```

## Async Processing Patterns

### Background Task Processing
```python
import asyncio
from typing import Callable, Any
from concurrent.futures import ThreadPoolExecutor

class BackgroundProcessor:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks = set()

    async def run_cpu_bound(self, func: Callable, *args) -> Any:
        """Run CPU-intensive tasks in background"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    def schedule_background_task(self, coro) -> asyncio.Task:
        """Schedule a background coroutine task"""
        task = asyncio.create_task(coro)
        self.running_tasks.add(task)

        # Remove task when it's done
        task.add_done_callback(lambda t: self.running_tasks.discard(t))

        return task

    async def shutdown(self):
        """Shutdown background processor"""
        # Cancel all running tasks
        for task in self.running_tasks:
            task.cancel()

        # Wait for tasks to finish
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)

        # Shutdown executor
        self.executor.shutdown(wait=True)

# Usage in MCP server
# processor = BackgroundProcessor()
#
# @server.handler.register_tool(
#     Tool(
#         name="background-process",
#         description="Process data in background",
#         inputSchema={"type": "object", "properties": {"data": {"type": "string"}}}
#     )
# )
# async def background_process_handler(params):
#     data = params["data"]
#
#     # Schedule background processing
#     task = processor.schedule_background_task(
#         process_large_dataset(data)
#     )
#
#     return {"message": "Processing scheduled", "task_id": id(task)}
```

### Streaming Resource Updates
```python
from mcp.types import TextResourceContents
import asyncio
from typing import AsyncGenerator

class StreamingResourceProvider:
    def __init__(self, server: Server):
        self.server = server
        self.stream_handlers = {}

    def register_streaming_resource(self, template_uri: str, name: str, description: str):
        """Register a resource that streams updates"""
        def decorator(gen_func):
            async def stream_resource(*args, **kwargs):
                # Create async generator
                async def content_generator():
                    async for chunk in gen_func(*args, **kwargs):
                        yield TextResourceContents(
                            text=chunk,
                            mimeType="text/plain"
                        )

                return content_generator()

            @self.server.handler.register_resource_template(
                ResourceTemplate(
                    uriTemplate=template_uri,
                    name=name,
                    description=description
                )
            )
            async def handler(*args, **kwargs):
                return await stream_resource(*args, **kwargs)

            return handler
        return decorator

# Example: Streaming log updates
# @streaming_provider.register_streaming_resource(
#     "urn:logs:stream",
#     "log-stream",
#     "Streaming log updates"
# )
# async def log_stream_handler():
#     # Simulate streaming logs
#     for i in range(10):
#         yield f"Log entry {i}\n"
#         await asyncio.sleep(1)
```

## Memory Management

### Resource Size Optimization
```python
import json
from typing import Any, Dict
import sys

class MemoryEfficientSerializer:
    @staticmethod
    def serialize_with_size_limit(obj: Any, max_size: int = 10 * 1024 * 1024) -> str:  # 10MB
        """Serialize object with size limit"""
        serialized = json.dumps(obj)

        if len(serialized.encode('utf-8')) > max_size:
            raise ValueError(f"Serialized object exceeds size limit: {max_size} bytes")

        return serialized

    @staticmethod
    def deserialize_with_validation(json_str: str) -> Any:
        """Deserialize with validation"""
        # Check size first
        if len(json_str.encode('utf-8')) > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("JSON string too large")

        return json.loads(json_str)

    @staticmethod
    def chunk_large_data(data: list, chunk_size: int = 1000) -> list:
        """Chunk large datasets for efficient processing"""
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        return chunks
```

## Load Balancing and Scaling

### Health Check Implementation
```python
from datetime import datetime, timedelta
import psutil
import time

class HealthChecker:
    def __init__(self, server):
        self.server = server
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.last_check = time.time()

    def increment_request(self):
        """Increment request counter"""
        self.request_count += 1

    def increment_error(self):
        """Increment error counter"""
        self.error_count += 1

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        uptime = datetime.now() - self.start_time

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent

        # Calculate error rate
        error_rate = (self.error_count / max(self.request_count, 1)) * 100

        # Determine health status
        is_healthy = (
            cpu_percent < 80 and
            memory_percent < 80 and
            error_rate < 5 and
            uptime.total_seconds() > 0  # Server is running
        )

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "uptime_seconds": int(uptime.total_seconds()),
            "requests_processed": self.request_count,
            "errors_encountered": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "timestamp": datetime.now().isoformat()
        }

# Integration with MCP server
class HealthCheckServer:
    def __init__(self, server):
        self.server = server
        self.health_checker = HealthChecker(server)

    def register_health_check_endpoint(self):
        """Register health check resource"""
        @self.server.handler.register_resource_template(
            ResourceTemplate(
                uriTemplate="urn:health:status",
                name="health-status",
                description="Server health status"
            )
        )
        def health_status_handler():
            return self.health_checker.get_health_status()

    def wrap_tool_handler(self, tool):
        """Wrap tool handler to track health metrics"""
        def decorator(func):
            @self.server.handler.register_tool(tool)
            def wrapper(*args, **kwargs):
                self.health_checker.increment_request()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.health_checker.increment_error()
                    raise e
            return wrapper
        return decorator
```

## Performance Monitoring

### Metrics Collection
```python
from collections import deque
from datetime import datetime, timedelta
import time

class PerformanceMetrics:
    def __init__(self, window_size: int = 1000):
        self.request_times = deque(maxlen=window_size)
        self.error_rates = deque(maxlen=window_size)
        self.active_requests = 0
        self.start_time = time.time()

    def start_request_timer(self) -> float:
        """Start timing a request"""
        self.active_requests += 1
        return time.time()

    def end_request_timer(self, start_time: float, success: bool = True):
        """End timing a request"""
        duration = time.time() - start_time
        self.request_times.append(duration)

        error_rate = 0 if success else 1
        self.error_rates.append(error_rate)

        self.active_requests -= 1

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        if not self.request_times:
            return {
                "avg_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
                "requests_per_second": 0,
                "active_requests": self.active_requests,
                "uptime_seconds": time.time() - self.start_time
            }

        # Calculate response time percentiles
        sorted_times = sorted(list(self.request_times))
        n = len(sorted_times)

        avg_response_time = sum(self.request_times) / n
        p95_idx = int(0.95 * n)
        p99_idx = int(0.99 * n)

        p95_response_time = sorted_times[min(p95_idx, n-1)] if n > 0 else 0
        p99_response_time = sorted_times[min(p99_idx, n-1)] if n > 0 else 0

        # Calculate requests per second (over last minute if available)
        if len(self.request_times) > 0:
            time_range = max(sorted_times[-1], 1)  # Avoid division by zero
            reqs_per_sec = len(self.request_times) / time_range
        else:
            reqs_per_sec = 0

        return {
            "avg_response_time": round(avg_response_time, 4),
            "p95_response_time": round(p95_response_time, 4),
            "p99_response_time": round(p99_response_time, 4),
            "requests_per_second": round(reqs_per_sec, 2),
            "active_requests": self.active_requests,
            "uptime_seconds": time.time() - self.start_time,
            "total_requests": len(self.request_times)
        }
```

## Complete Performance-Optimized Example

```python
def create_high_performance_mcp_server():
    """Create a complete high-performance MCP server"""
    from mcp.server import Server
    from mcp.types import Tool

    server = Server("high-perf-mcp-server")

    # Initialize performance components
    cache = ResourceCache(default_ttl=300)
    health_checker = HealthChecker(server)
    perf_metrics = PerformanceMetrics(window_size=1000)
    bg_processor = BackgroundProcessor(max_workers=4)

    # Register health check endpoint
    @server.handler.register_resource_template(
        ResourceTemplate(
            uriTemplate="urn:health:metrics",
            name="performance-metrics",
            description="Performance metrics endpoint"
        )
    )
    def health_metrics_handler():
        return {
            "health": health_checker.get_health_status(),
            "performance": perf_metrics.get_performance_stats()
        }

    # Register a cached, performance-monitored tool
    @server.handler.register_tool(
        Tool(
            name="optimized-operation",
            description="High-performance operation with caching and monitoring",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "data": {"type": "array", "items": {"type": "number"}}
                },
                "required": ["operation", "data"]
            }
        )
    )
    async def optimized_operation_handler(params):
        # Start performance timer
        start_time = perf_metrics.start_request_timer()

        try:
            operation = params["operation"]
            data = params["data"]

            # Create cache key
            cache_key = f"operation:{operation}:{hash(str(data))}"

            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result:
                perf_metrics.end_request_timer(start_time, success=True)
                return cached_result

            # Perform operation
            if operation == "sum":
                result = sum(data)
            elif operation == "average":
                result = sum(data) / len(data) if data else 0
            elif operation == "max":
                result = max(data) if data else 0
            else:
                result = {"error": "Unknown operation"}

            # Cache result
            await cache.set(cache_key, result, ttl=600)  # 10 minute cache

            # End performance timer
            perf_metrics.end_request_timer(start_time, success=True)

            return {"result": result, "cached": False}

        except Exception as e:
            # End performance timer with error
            perf_metrics.end_request_timer(start_time, success=False)
            health_checker.increment_error()
            raise e

    # Register cleanup on shutdown
    async def cleanup():
        await bg_processor.shutdown()

    return server, cleanup

# Usage
# server, cleanup = create_high_performance_mcp_server()
#
# try:
#     # Run server
#     from mcp.server.stdio import stdio_server
#     import sys
#
#     with stdio_server(server, sys.stdin, sys.stdout):
#         server.run()
# finally:
#     asyncio.run(cleanup())
```