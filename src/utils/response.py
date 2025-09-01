"""Standardized response utilities for MCP tools."""

from typing import Any, Dict, List, Optional, Union


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


def batch_response(
    results: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a response for batch operations.
    
    Args:
        results: List of individual operation results
        summary: Optional summary statistics
        
    Returns:
        Standardized batch response
    """
    # Check if any operation failed
    all_ok = all(r.get("ok", True) for r in results)
    
    data = {"results": results}
    
    if summary:
        data["summary"] = summary
    
    # Count successes and failures
    success_count = sum(1 for r in results if r.get("ok", True))
    failure_count = len(results) - success_count
    
    data["stats"] = {
        "total": len(results),
        "success": success_count,
        "failure": failure_count
    }
    
    return {
        "ok": all_ok,
        "data": data
    }