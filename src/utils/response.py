"""Standardized response utilities for MCP tools."""

from typing import Any, Dict, List, Optional, Union


def is_success(result: Dict[str, Any]) -> bool:
    """Check if operation succeeded regardless of response format.
    
    Handles both new format {"ok": true} and legacy {"status": "success"}.
    """
    return bool(result.get("ok") or result.get("status") == "success")


def success_response(
    data: Any,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a successful response envelope.
    
    Args:
        data: The response data
        warnings: Optional list of warning messages
        
    Returns:
        Standardized success response
    """
    response = {
        "ok": True,
        "data": data
    }
    
    if warnings:
        response["warnings"] = warnings
    
    return response


def error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response envelope.
    
    Args:
        message: Error message
        code: Optional error code
        details: Optional error details
        
    Returns:
        Standardized error response
    """
    error = {"message": message}
    
    if code:
        error["code"] = code
    
    if details:
        error["details"] = details
    
    return {
        "ok": False,
        "error": error
    }


def validation_response(
    status: str,
    issues: Optional[List[Dict[str, Any]]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a validation response with structured issues.
    
    Args:
        status: Overall status ("ok", "warning", "error")
        issues: List of validation issues
        metrics: Optional metrics/statistics
        warnings: Optional warning messages
        
    Returns:
        Standardized validation response
    """
    data = {"status": status}
    
    if issues:
        data["issues"] = issues
    else:
        data["issues"] = []
    
    if metrics:
        data["metrics"] = metrics
    
    response = {
        "ok": status != "error",
        "data": data
    }
    
    if warnings:
        response["warnings"] = warnings
    
    return response


def create_issue(
    severity: str,
    message: str,
    location: Optional[str] = None,
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a structured validation issue.
    
    Args:
        severity: Issue severity ("error", "warning", "info")
        message: Issue message
        location: Optional location (node ID, edge ID, etc.)
        code: Optional issue code
        details: Optional additional details
        
    Returns:
        Structured issue dictionary
    """
    issue = {
        "severity": severity,
        "message": message
    }
    
    if location:
        issue["location"] = location
    
    if code:
        issue["code"] = code
    
    if details:
        issue["details"] = details
    
    return issue