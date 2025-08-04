"""
API trace decorators and utilities for adding distributed tracing to API routes.

This module provides easy-to-use decorators for API route functions 
to enable rich distributed tracing with Tempo integration.
"""
import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, Optional, Union

from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode

from app.core.tempo.core import get_tempo
from app.core.telemetry.telemetry import get_telemetry

logger = logging.getLogger(__name__)


def trace_api_route(
    operation_name: Optional[str] = None,
    include_request_body: bool = False,
    include_response_body: bool = False,
    include_headers: bool = False,
    include_query_params: bool = True,
    include_path_params: bool = True,
):
    """
    Decorator for FastAPI route handlers to add distributed tracing.
    
    Creates spans in both telemetry and Tempo systems with request details
    as span attributes for better visualization in Grafana Tempo.
    
    Args:
        operation_name: Optional custom name for the span. If not provided, 
                        the function name will be used.
        include_request_body: Whether to include the request body in the span
        include_response_body: Whether to include the response body in the span
        include_headers: Whether to include request headers in the span
        include_query_params: Whether to include query parameters in the span
        include_path_params: Whether to include path parameters in the span
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get('request')
            
            # Use function name if operation_name is not provided
            span_name = operation_name or f"api.{func.__name__}"
            
            # Extract request information for span attributes
            attributes = {}
            if request:
                # Extract route path - fix for APIRoute object error
                route_path = "unknown"
                if "route" in request.scope:
                    route = request.scope["route"]
                    if hasattr(route, "path"):
                        route_path = route.path
                
                attributes.update({
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.route": route_path,
                })
                
                # Add query params if requested
                if include_query_params:
                    for key, value in request.query_params.items():
                        attributes[f"http.query.{key}"] = value
                
                # Add path params if requested
                if include_path_params:
                    path_params = request.path_params
                    for key, value in path_params.items():
                        attributes[f"http.path.{key}"] = str(value)
                
                # Add headers if requested
                if include_headers:
                    for key, value in request.headers.items():
                        # Skip sensitive headers like authorization
                        if key.lower() not in ["authorization", "cookie"]:
                            attributes[f"http.header.{key}"] = value
                
                # Add request body if requested
                if include_request_body:
                    try:
                        # This is a bit tricky because request.body() is async and can only be called once
                        # We'd need to modify the FastAPI app to store the body in request.state
                        # For now, skip this feature
                        pass
                    except Exception as e:
                        logger.warning(f"Failed to capture request body: {e}")
            
            # Get both telemetry and tempo clients
            try:
                telemetry_client = get_telemetry()
            except RuntimeError:
                telemetry_client = None
            
            try:
                tempo_client = get_tempo()
            except RuntimeError:
                tempo_client = None
                logger.warning("Tempo client not initialized, tracing will be limited")
            
            # Add a timestamp for performance tracking
            start_time = time.time()
            
            # Define function to create span and execute the original function
            async def execute_with_span():
                try:
                    # Use tempo client if available, otherwise fallback to telemetry
                    client = tempo_client or telemetry_client
                    if not client:
                        # If neither client is available, just execute the function
                        return await func(*args, **kwargs)
                    
                    with client.create_span(span_name, attributes) as span:
                        try:
                            # Execute the original function
                            response = await func(*args, **kwargs)
                            
                            # Add response information to span
                            try:
                                if isinstance(response, Response):
                                    span.set_attribute("http.status_code", response.status_code)
                                    
                                    # Add response body if requested and it's a JSON response
                                    if include_response_body and hasattr(response, "body"):
                                        try:
                                            # Limit size to avoid bloating spans
                                            body_str = response.body.decode("utf-8")
                                            if len(body_str) <= 4096:  # Limit to 4KB
                                                span.set_attribute("http.response.body", body_str)
                                        except Exception as e:
                                            logger.warning(f"Failed to capture response body: {e}")
                            except Exception as attr_error:
                                logger.warning(f"Error adding response attributes to span: {attr_error}")
                            
                            # Add performance information
                            try:
                                span.set_attribute("duration_ms", (time.time() - start_time) * 1000)
                                span.set_status(Status(StatusCode.OK))
                            except Exception as perf_error:
                                logger.warning(f"Error adding performance metrics to span: {perf_error}")
                            
                            return response
                        except Exception as e:
                            # Record exception and set error status
                            try:
                                span.record_exception(e)
                                span.set_status(Status(StatusCode.ERROR))
                                span.set_attribute("error.message", str(e))
                                span.set_attribute("error.type", e.__class__.__name__)
                            except Exception as span_error:
                                logger.warning(f"Error recording exception in span: {span_error}")
                            
                            # Re-raise the exception
                            raise
                except Exception as outer_error:
                    # Last resort fallback - if anything in the tracing code fails,
                    # log it and still try to execute the original function
                    logger.error(f"Tracing error in {span_name}: {outer_error}")
                    return await func(*args, **kwargs)
            
            # Execute the function with the span
            return await execute_with_span()
        
        # Handle synchronous functions too
        if not inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(wrapper(*args, **kwargs))
            return sync_wrapper
        
        return wrapper
    
    return decorator


def trace_db_operation(
    operation: str, 
    table: Optional[str] = None, 
    include_parameters: bool = True
):
    """
    Decorator for database operations to add distributed tracing.
    
    Creates spans in both telemetry and Tempo systems with database operation
    details for better visualization in Grafana Tempo.
    
    Args:
        operation: Type of database operation (select, insert, update, delete)
        table: Optional table name
        include_parameters: Whether to include operation parameters in the span
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get telemetry and tempo clients
            try:
                telemetry_client = get_telemetry()
            except RuntimeError:
                telemetry_client = None
            
            try:
                tempo_client = get_tempo()
            except RuntimeError:
                tempo_client = None
                logger.warning("Tempo client not initialized, tracing will be limited")
            
            # Skip if neither client is available
            if not telemetry_client and not tempo_client:
                return await func(*args, **kwargs)
            
            # Prepare span attributes
            attributes = {
                "db.operation": operation,
            }
            
            if table:
                attributes["db.table"] = table
            
            # Add function parameters if requested
            if include_parameters:
                # Skip first argument if it's self or cls
                skip_first = len(args) > 0 and args[0].__class__.__name__ == func.__qualname__.split('.')[0]
                
                # Add args (excluding self/cls)
                for i, arg in enumerate(args[1:] if skip_first else args):
                    # Skip request objects and limit string length
                    if not isinstance(arg, Request):
                        arg_str = str(arg)
                        if len(arg_str) <= 256:  # Limit string length
                            attributes[f"db.arg.{i}"] = arg_str
                
                # Add kwargs
                for key, value in kwargs.items():
                    # Skip password and sensitive keys, limit string length
                    if "password" not in key.lower() and "secret" not in key.lower():
                        value_str = str(value)
                        if len(value_str) <= 256:  # Limit string length
                            attributes[f"db.kwarg.{key}"] = value_str
            
            # Use tempo client if available, otherwise fallback to telemetry
            client = tempo_client or telemetry_client
            
            try:
                # Record the DB operation in both systems
                with client.create_span(f"db.{operation}", attributes) as span:
                    try:
                        # Add timestamp for performance tracking
                        start_time = time.time()
                        
                        # Execute the function
                        result = await func(*args, **kwargs)
                        
                        try:
                            # Add duration information
                            span.set_attribute("duration_ms", (time.time() - start_time) * 1000)
                            
                            # Set success status
                            span.set_status(Status(StatusCode.OK))
                        except Exception as attr_error:
                            logger.warning(f"Error adding attributes to DB span: {attr_error}")
                        
                        return result
                    except Exception as e:
                        # Record exception and set error status
                        try:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR))
                            span.set_attribute("error.message", str(e))
                            span.set_attribute("error.type", e.__class__.__name__)
                        except Exception as span_error:
                            logger.warning(f"Error recording exception in DB span: {span_error}")
                        
                        # Re-raise the exception
                        raise
            except Exception as tracing_error:
                # If tracing fails, still execute the original function
                logger.error(f"Tracing error in DB operation {operation}: {tracing_error}")
                return await func(*args, **kwargs)
        
        # Handle synchronous functions
        if not inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(wrapper(*args, **kwargs))
            return sync_wrapper
        
        return wrapper
    
    return decorator
