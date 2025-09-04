import glob
import io
import logging
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP
from RestrictedPython import compile_restricted_exec
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    safe_builtins,
    safe_globals,
)
from RestrictedPython.PrintCollector import PrintCollector

# Configure logging with environment variable control
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Workaround for https://github.com/modelcontextprotocol/python-sdk/issues/1273
# Environment variables FASTMCP_HOST and FASTMCP_PORT don't work automatically,
# so we read them manually and pass to constructor
host = os.getenv("FASTMCP_HOST", "0.0.0.0")
port = int(os.getenv("FASTMCP_PORT", "8000"))

mcp = FastMCP("tabular-data-mcp", host=host, port=port)

# Global configuration
DATA_DIRECTORY = "./data"


def ensure_data_directory():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIRECTORY):
        os.makedirs(DATA_DIRECTORY)


def create_safe_namespace():
    """Create a safe execution namespace with whitelisted modules and functions"""
    # Start with RestrictedPython's safe globals
    namespace = safe_globals.copy()

    # Add safe built-ins
    namespace["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
    namespace["__name__"] = "__restricted__"
    # Print will be handled by PrintCollector instance in run_python_code

    # Add essential guards for item access
    namespace["_getitem_"] = lambda obj, index: obj[index]
    namespace["_getiter_"] = iter
    namespace["_getattr_"] = getattr
    namespace["_write_"] = lambda x: x

    # Safe import function that only allows whitelisted modules
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        allowed_modules = {
            "pandas",
            "pd",
            "numpy",
            "np",
            "matplotlib",
            "matplotlib.pyplot",
            "openpyxl",
            "json",
            "math",
            "statistics",
            "datetime",
            "re",
        }

        if name in allowed_modules:
            if name == "pandas":
                import pandas

                return pandas
            elif name == "numpy":
                try:
                    import numpy

                    return numpy
                except ImportError:
                    raise ImportError(f"Module {name} not available")
            elif name == "matplotlib.pyplot":
                try:
                    import matplotlib.pyplot as plt

                    plt.switch_backend("Agg")  # Non-interactive backend
                    return plt
                except ImportError:
                    raise ImportError(f"Module {name} not available")
            elif name in ["json", "math", "statistics", "datetime", "re"]:
                return __import__(name)

        raise ImportError(f"Module '{name}' is not allowed in restricted environment")

    namespace["__import__"] = safe_import

    # Add data science libraries (these are generally safe for data analysis)
    try:
        import pandas as pd

        namespace["pd"] = pd
        namespace["pandas"] = pd
    except ImportError:
        pass

    try:
        import numpy as np

        namespace["np"] = np
        namespace["numpy"] = np
    except ImportError:
        pass

    try:
        import matplotlib.pyplot as plt

        # Restrict matplotlib to non-interactive backends for safety
        plt.switch_backend("Agg")  # Non-interactive backend
        namespace["plt"] = plt
        namespace["matplotlib"] = __import__("matplotlib")
    except ImportError:
        pass

    try:
        import openpyxl

        namespace["openpyxl"] = openpyxl
    except ImportError:
        pass

    # Add safe Path class for data directory access only
    class SafePath:
        def __init__(self, path):
            # Only allow access to files in the data directory
            abs_path = os.path.abspath(path)
            data_abs = os.path.abspath(DATA_DIRECTORY)
            if not abs_path.startswith(data_abs):
                raise PermissionError(
                    f"Access denied: Path must be within {DATA_DIRECTORY}"
                )
            self._path = Path(path)

        def __getattr__(self, name):
            return getattr(self._path, name)

    namespace["Path"] = SafePath

    # Add safe file operations (restricted to data directory)
    def safe_open(filename, mode="r", **kwargs):
        file_path = os.path.join(DATA_DIRECTORY, filename)
        # Ensure we stay within data directory
        abs_path = os.path.abspath(file_path)
        data_abs = os.path.abspath(DATA_DIRECTORY)
        if not abs_path.startswith(data_abs):
            raise PermissionError(
                f"Access denied: Can only open files in {DATA_DIRECTORY}"
            )
        return open(file_path, mode, **kwargs)

    namespace["open"] = safe_open

    # Add some safe built-in functions
    namespace["len"] = len
    namespace["str"] = str
    namespace["int"] = int
    namespace["float"] = float
    namespace["list"] = list
    namespace["dict"] = dict
    namespace["tuple"] = tuple
    namespace["set"] = set
    namespace["bool"] = bool
    namespace["range"] = range
    namespace["enumerate"] = enumerate
    namespace["zip"] = zip
    namespace["sum"] = sum
    namespace["min"] = min
    namespace["max"] = max
    namespace["abs"] = abs
    namespace["round"] = round
    namespace["sorted"] = sorted
    namespace["reversed"] = reversed
    namespace["print"] = print

    # Add some safe modules
    import datetime
    import json
    import math
    import re
    import statistics

    namespace["json"] = json
    namespace["math"] = math
    namespace["statistics"] = statistics
    namespace["datetime"] = datetime
    namespace["re"] = re

    return namespace


@mcp.tool()
def list_data_files() -> str:
    """List all available CSV and Excel files in the data directory"""
    ensure_data_directory()

    csv_files = glob.glob(os.path.join(DATA_DIRECTORY, "*.csv"))
    excel_files = glob.glob(os.path.join(DATA_DIRECTORY, "*.xlsx")) + glob.glob(
        os.path.join(DATA_DIRECTORY, "*.xls")
    )

    all_files = []

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        all_files.append(f"{filename} (CSV, {file_size} bytes)")

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        all_files.append(f"{filename} (Excel, {file_size} bytes)")

    if not all_files:
        return "No CSV or Excel files found in the data directory. Please add files to ./data/"

    return "Available data files:\n" + "\n".join(all_files)


@mcp.tool()
def list_sheets(filename: str) -> str:
    """List all sheets in an Excel file"""
    file_path = os.path.join(DATA_DIRECTORY, filename)

    if not os.path.exists(file_path):
        return f"File '{filename}' not found in data directory."

    if not filename.lower().endswith((".xlsx", ".xls")):
        return f"'{filename}' is not an Excel file. This tool only works with .xlsx and .xls files."

    try:
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names

        sheet_info = []
        for sheet in sheets:
            df = pd.read_excel(file_path, sheet_name=sheet)
            rows, cols = df.shape
            sheet_info.append(f"{sheet} ({rows} rows, {cols} columns)")

        return f"Sheets in '{filename}':\n" + "\n".join(sheet_info)

    except Exception as e:
        return f"Error reading Excel file: {str(e)}"


@mcp.tool()
def run_python_code(code: str) -> str:
    """Execute Python code in a restricted environment using RestrictedPython.

    Pre-imported libraries (no import statements needed):
    - pandas (as 'pd' and 'pandas')
    - numpy (as 'np' and 'numpy')
    - matplotlib.pyplot (as 'plt')
    - openpyxl
    - Standard library: json, math, statistics, datetime, re

    File access is restricted to the ./data directory only.

    Do not include any import statements in the code, as these are not allowed and it will fail the code execution.
    """

    # Log the code being executed for debugging
    logging.debug("=" * 60)
    logging.debug("EXECUTING PYTHON CODE:")
    logging.debug("=" * 60)
    for i, line in enumerate(code.split("\n"), 1):
        logging.debug(f"{i:3d} | {line}")
    logging.debug("=" * 60)

    try:
        # Compile the code using RestrictedPython
        compiled_code = compile_restricted_exec(code)

        # Check for compilation errors
        if compiled_code.errors:
            error_msg = "RestrictedPython compilation errors:\n"
            for error in compiled_code.errors:
                error_msg += f"- {error}\n"
            return error_msg

        # Allow execution with warnings but show them
        warnings_text = ""
        if compiled_code.warnings:
            warnings_text = (
                "WARNING - RestrictedPython detected potentially unsafe patterns:\n"
            )
            for warning in compiled_code.warnings:
                warnings_text += f"- {warning}\n"
            warnings_text += "\n"

        # Create safe namespace
        namespace = create_safe_namespace()

        # Create custom print collector for this execution
        class CustomPrintCollector:
            def __init__(self):
                self.collected = []

            def __call__(self, *args, **kwargs):
                # This returns self so that _call_print can be called
                return self

            def _call_print(self, *args, **kwargs):
                # Convert args to strings and collect them
                output = " ".join(str(arg) for arg in args)
                self.collected.append(output)
                # Don't also print to stdout to avoid duplicates

        print_collector = CustomPrintCollector()
        namespace["_print_"] = print_collector

        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        # Execute the restricted code with output capture
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(compiled_code.code, namespace)

        # Get captured output
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()
        print_output = (
            "\n".join(print_collector.collected) if print_collector.collected else ""
        )

        # Combine outputs
        output_parts = []
        if warnings_text:
            output_parts.append(warnings_text.rstrip())
        if print_output:
            output_parts.append(print_output.rstrip())
        if stdout_output:
            output_parts.append(stdout_output.rstrip())
        if stderr_output:
            output_parts.append(f"stderr: {stderr_output.rstrip()}")

        if not print_output and not stdout_output and not stderr_output:
            if warnings_text:
                output_parts.append(
                    "Code executed successfully in restricted environment (no output produced)"
                )
            else:
                return "Code executed successfully in restricted environment (no output produced)"

        return "\n".join(output_parts)

    except Exception as e:
        # Get the full traceback for debugging
        error_traceback = traceback.format_exc()
        return (
            f"Error executing Python code in restricted environment:\n{error_traceback}"
        )


@mcp.tool()
def list_available_python_libs() -> str:
    """List available Python libraries in the execution environment"""
    libraries = [
        "pandas - Data manipulation and analysis",
        "numpy - Numerical computing",
        "matplotlib - Plotting and visualization",
        "openpyxl - Excel file reading/writing",
        "Standard library: os, json, csv, datetime, re, math, statistics, io, pathlib",
    ]

    result = "Available Python libraries:\n"
    result += "\n".join([f"- {lib}" for lib in libraries])
    result += "\n\nNote: Use list_data_files and list_sheets tools to see available data files."
    result += "\nYou'll need to load data files manually in your code using pandas.read_csv() or pandas.read_excel()."

    return result


if __name__ == "__main__":
    transport = os.getenv("FASTMCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
