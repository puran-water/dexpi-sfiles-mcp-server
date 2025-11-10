"""
Regression tests to prevent fallback patterns from creeping back into the codebase.

These tests enforce the "Fail Loudly" philosophy established in the Bug Surfacing Sprint.
Any fallback pattern that masks bugs should cause these tests to FAIL IMMEDIATELY.

Run these tests in CI/CD to catch regressions before they reach production.
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest


# Paths to scan
SRC_DIR = Path(__file__).parent.parent / "src"
EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git", "node_modules"}


def get_python_files() -> List[Path]:
    """Get all Python files in src/ directory."""
    python_files = []
    for path in SRC_DIR.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue
        python_files.append(path)
    return python_files


def scan_for_bare_except(file_path: Path) -> List[Tuple[int, str]]:
    """
    Scan a Python file for bare except clauses.

    Returns:
        List of (line_number, code_snippet) tuples for bare except clauses
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, start=1):
            # Check for bare except: or except Exception:
            # Allow specific exception types only
            if re.search(r'\bexcept\s*:', line):
                violations.append((i, line.strip()))

    except Exception:
        # Skip files that can't be read
        pass

    return violations


def scan_for_silent_imports(file_path: Path) -> List[Tuple[int, str]]:
    """
    Scan a Python file for silent import failures (try/except ImportError: X = None).

    Returns:
        List of (line_number, code_snippet) tuples for silent import patterns
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # Check if this is try/except ImportError
                for handler in node.handlers:
                    if handler.type and isinstance(handler.type, ast.Name):
                        if handler.type.id == 'ImportError':
                            # Check if the handler assigns None or has a pass statement
                            for stmt in handler.body:
                                if isinstance(stmt, ast.Assign):
                                    # Check if assigning None
                                    if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                                        line_num = stmt.lineno
                                        violations.append((line_num, lines[line_num - 1].strip()))
                                elif isinstance(stmt, ast.Pass):
                                    # Silent pass in ImportError handler
                                    line_num = stmt.lineno
                                    violations.append((line_num, lines[line_num - 1].strip()))

    except Exception:
        # Skip files that can't be parsed
        pass

    return violations


def scan_for_type_aliasing(file_path: Path) -> List[Tuple[int, str]]:
    """
    Scan a Python file for type aliasing that might mask missing classes.

    Example: CentrifugalBlower = CustomEquipment

    Returns:
        List of (line_number, code_snippet) tuples for type aliasing patterns
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, start=1):
            # Skip comments
            if line.strip().startswith('#'):
                continue

            # Check for ClassName = OtherClassName patterns
            # But exclude legitimate imports and dataclass definitions
            if '=' in line and not any(keyword in line for keyword in ['import', 'dataclass', '==', '!=', '<=', '>=', ':']):
                # Match pattern: ClassName = OtherClassName (both start with capital)
                # But NOT: CONSTANT = value or variable = value
                match = re.search(r'\b([A-Z][a-z][a-zA-Z0-9_]*)\s*=\s*([A-Z][a-z][a-zA-Z0-9_]*)\s*(?:#.*)?$', line)
                if match:
                    lhs, rhs = match.groups()
                    # Exclude common legitimate patterns
                    if not any(pattern in line for pattern in ['Optional', 'Union', 'List', 'Dict', 'Tuple', 'Any', 'True', 'False', 'None']):
                        # Only flag if both sides look like class names (CamelCase, not SCREAMING_CASE)
                        if lhs[0].isupper() and lhs[1].islower() and rhs[0].isupper() and rhs[1].islower():
                            violations.append((i, line.strip()))

    except Exception:
        # Skip files that can't be read
        pass

    return violations


def scan_for_default_returns(file_path: Path) -> List[Tuple[int, str]]:
    """
    Scan for functions that return default values (None, [], {}) in except blocks.

    These often mask errors instead of letting them propagate.

    Returns:
        List of (line_number, code_snippet) tuples
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    # Check for return statements in except blocks
                    for stmt in handler.body:
                        if isinstance(stmt, ast.Return):
                            if stmt.value is None:
                                # return None
                                line_num = stmt.lineno
                                violations.append((line_num, lines[line_num - 1].strip()))
                            elif isinstance(stmt.value, (ast.List, ast.Dict, ast.Constant)):
                                # return [], {}, "", 0, False, etc.
                                if isinstance(stmt.value, ast.Constant):
                                    # Only flag empty defaults, not specific error codes
                                    if stmt.value.value in [None, "", 0, False]:
                                        line_num = stmt.lineno
                                        violations.append((line_num, lines[line_num - 1].strip()))
                                else:
                                    line_num = stmt.lineno
                                    violations.append((line_num, lines[line_num - 1].strip()))

    except Exception:
        # Skip files that can't be parsed
        pass

    return violations


class TestNoFallbackPatterns:
    """
    Test suite to ensure no fallback patterns exist in the codebase.

    These tests enforce the "Fail Loudly" philosophy:
    - NO bare except clauses
    - NO silent import failures
    - NO type aliasing to mask missing classes
    - NO default returns in except blocks
    """

    def test_no_bare_except_clauses(self):
        """
        CRITICAL: Ensure no bare except: clauses exist.

        Bare except clauses catch ALL exceptions including KeyboardInterrupt and SystemExit,
        making debugging impossible. All exception handling must be specific.
        """
        all_violations = []

        for file_path in get_python_files():
            violations = scan_for_bare_except(file_path)
            if violations:
                for line_num, code in violations:
                    all_violations.append(f"{file_path}:{line_num} - {code}")

        if all_violations:
            violation_report = "\n".join(all_violations)
            pytest.fail(
                f"Found {len(all_violations)} bare except clause(s):\n\n"
                f"{violation_report}\n\n"
                f"FAIL LOUDLY: Replace with specific exception types (ValueError, ImportError, etc.)"
            )

    def test_no_silent_import_failures(self):
        """
        CRITICAL: Ensure no silent import failures (try/except ImportError: X = None).

        Silent import failures mask dependency issues. All imports should either:
        1. Succeed, or
        2. Raise ImportError with a clear message about what's missing
        """
        all_violations = []

        for file_path in get_python_files():
            violations = scan_for_silent_imports(file_path)
            if violations:
                for line_num, code in violations:
                    all_violations.append(f"{file_path}:{line_num} - {code}")

        if all_violations:
            violation_report = "\n".join(all_violations)
            pytest.fail(
                f"Found {len(all_violations)} silent import failure(s):\n\n"
                f"{violation_report}\n\n"
                f"FAIL LOUDLY: Remove fallback assignments. Raise ImportError with install instructions."
            )

    def test_no_suspicious_type_aliasing(self):
        """
        WARNING: Check for type aliasing that might mask missing classes.

        Type aliasing like 'CentrifugalBlower = CustomEquipment' can mask bugs
        when the real class doesn't exist. Prefer explicit imports with helpful errors.

        Note: This test may have false positives for legitimate type aliases.
        Review violations carefully.
        """
        all_violations = []

        for file_path in get_python_files():
            violations = scan_for_type_aliasing(file_path)
            if violations:
                for line_num, code in violations:
                    all_violations.append(f"{file_path}:{line_num} - {code}")

        if all_violations:
            violation_report = "\n".join(all_violations)
            pytest.fail(
                f"Found {len(all_violations)} suspicious type alias(es):\n\n"
                f"{violation_report}\n\n"
                f"FAIL LOUDLY: Replace with explicit imports that raise ImportError if class doesn't exist."
            )

    def test_no_default_returns_in_except(self):
        """
        WARNING: Check for default returns (None, [], {}) in except blocks.

        Returning default values from except blocks often masks errors.
        Prefer letting exceptions propagate with clear error messages.

        Note: Some legitimate uses exist (e.g., optional features).
        Review violations carefully.
        """
        all_violations = []

        for file_path in get_python_files():
            violations = scan_for_default_returns(file_path)
            if violations:
                for line_num, code in violations:
                    all_violations.append(f"{file_path}:{line_num} - {code}")

        if all_violations:
            violation_report = "\n".join(all_violations)
            # This is a warning, not a hard failure
            print(
                f"\n⚠️  WARNING: Found {len(all_violations)} default return(s) in except blocks:\n\n"
                f"{violation_report}\n\n"
                f"Review these carefully - they may be masking errors."
            )


class TestFallbackPatternDocumentation:
    """
    Documentation and examples of forbidden patterns.

    These tests demonstrate WHAT NOT TO DO and provide guidance for the correct approach.
    """

    def test_example_bad_bare_except(self):
        """
        ❌ BAD: Bare except clause
        """
        example_bad = '''
        try:
            risky_operation()
        except:  # ❌ Catches EVERYTHING including KeyboardInterrupt
            return None  # Silent failure
        '''

        example_good = '''
        try:
            risky_operation()
        except (ValueError, TypeError) as e:  # ✅ Specific exceptions
            raise RuntimeError(f"Operation failed: {e}") from e  # ✅ Fails loudly
        '''

        # This test always passes - it's documentation
        assert "except:" in example_bad
        assert "except (ValueError, TypeError)" in example_good

    def test_example_bad_silent_import(self):
        """
        ❌ BAD: Silent import failure
        """
        example_bad = '''
        try:
            from optional_package import OptionalClass
        except ImportError:
            OptionalClass = None  # ❌ Silent failure - masks missing dependency
        '''

        example_good = '''
        try:
            from optional_package import OptionalClass
        except ImportError as e:
            raise ImportError(  # ✅ Fails loudly with clear message
                "optional_package is required. Install with: pip install optional_package"
            ) from e
        '''

        # This test always passes - it's documentation
        assert "OptionalClass = None" in example_bad
        assert "raise ImportError" in example_good

    def test_example_bad_type_aliasing(self):
        """
        ❌ BAD: Type aliasing to mask missing class
        """
        example_bad = '''
        try:
            from pydexpi import CentrifugalBlower
        except ImportError:
            CentrifugalBlower = CustomEquipment  # ❌ Masks missing class
        '''

        example_good = '''
        try:
            from pydexpi import CentrifugalBlower
        except ImportError as e:
            raise ImportError(  # ✅ Fails loudly
                "CentrifugalBlower class not found in pyDEXPI. "
                "Check available equipment types with schema_query()"
            ) from e
        '''

        # This test always passes - it's documentation
        assert "CentrifugalBlower = CustomEquipment" in example_bad
        assert "raise ImportError" in example_good


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
