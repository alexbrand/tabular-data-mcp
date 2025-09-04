import os
import glob
import logging
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from mcp.server.fastmcp import FastMCP

# Workaround for https://github.com/modelcontextprotocol/python-sdk/issues/1273
# Environment variables FASTMCP_HOST and FASTMCP_PORT don't work automatically,
# so we read them manually and pass to constructor
host = os.getenv("FASTMCP_HOST", "0.0.0.0")
port = int(os.getenv("FASTMCP_PORT", "8000"))

mcp = FastMCP("tabular-mcp", host=host, port=port)

# Global configuration
DATA_DIRECTORY = "./data"

def ensure_data_directory():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIRECTORY):
        os.makedirs(DATA_DIRECTORY)

@mcp.tool()
def list_data_files() -> str:
    """List all available CSV and Excel files in the data directory"""
    ensure_data_directory()
    
    csv_files = glob.glob(os.path.join(DATA_DIRECTORY, "*.csv"))
    excel_files = glob.glob(os.path.join(DATA_DIRECTORY, "*.xlsx")) + glob.glob(os.path.join(DATA_DIRECTORY, "*.xls"))
    
    all_files = []
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        all_files.append(f"📄 {filename} (CSV, {file_size} bytes)")
    
    for file_path in excel_files:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        all_files.append(f"📊 {filename} (Excel, {file_size} bytes)")
    
    if not all_files:
        return "No CSV or Excel files found in the data directory. Please add files to ./data/"
    
    return "Available data files:\n" + "\n".join(all_files)

@mcp.tool()
def list_sheets(filename: str) -> str:
    """List all sheets in an Excel file"""
    file_path = os.path.join(DATA_DIRECTORY, filename)
    
    if not os.path.exists(file_path):
        return f"File '{filename}' not found in data directory."
    
    if not filename.lower().endswith(('.xlsx', '.xls')):
        return f"'{filename}' is not an Excel file. This tool only works with .xlsx and .xls files."
    
    try:
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        
        sheet_info = []
        for sheet in sheets:
            df = pd.read_excel(file_path, sheet_name=sheet)
            rows, cols = df.shape
            sheet_info.append(f"📋 {sheet} ({rows} rows, {cols} columns)")
        
        return f"Sheets in '{filename}':\n" + "\n".join(sheet_info)
        
    except Exception as e:
        return f"Error reading Excel file: {str(e)}"

@mcp.tool()
def run_python_code(code: str) -> str:
    """Execute Python code directly (no sandboxing)"""
    try:
        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        # Create a namespace with common data science libraries
        namespace = {
            '__builtins__': __builtins__,
            'pd': pd,
            'pandas': pd,
            'os': os,
            'glob': glob,
            'Path': Path,
        }
        
        # Try to import additional libraries that might be available
        try:
            import numpy as np
            namespace['np'] = np
            namespace['numpy'] = np
        except ImportError:
            pass
            
        try:
            import matplotlib.pyplot as plt
            namespace['plt'] = plt
            namespace['matplotlib'] = __import__('matplotlib')
        except ImportError:
            pass
            
        try:
            import openpyxl
            namespace['openpyxl'] = openpyxl
        except ImportError:
            pass
        
        # Execute the code with output capture
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, namespace)
        
        # Get captured output
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()
        
        # Combine outputs
        output_parts = []
        if stdout_output:
            output_parts.append(stdout_output.rstrip())
        if stderr_output:
            output_parts.append(f"stderr: {stderr_output.rstrip()}")
        
        if output_parts:
            return "\n".join(output_parts)
        else:
            return "Code executed successfully (no output produced)"
            
    except Exception as e:
        # Get the full traceback for debugging
        error_traceback = traceback.format_exc()
        return f"Error executing Python code:\n{error_traceback}"

@mcp.tool()
def list_available_python_libs() -> str:
    """List available Python libraries in the execution environment"""
    libraries = [
        "pandas - Data manipulation and analysis",
        "numpy - Numerical computing", 
        "matplotlib - Plotting and visualization",
        "openpyxl - Excel file reading/writing",
        "Standard library: os, json, csv, datetime, re, math, statistics, io, pathlib"
    ]
    
    result = "Available Python libraries:\n"
    result += "\n".join([f"• {lib}" for lib in libraries])
    result += "\n\nNote: Use list_data_files and list_sheets tools to see available data files."
    result += "\nYou'll need to load data files manually in your code using pandas.read_csv() or pandas.read_excel()."
    
    return result

if __name__ == "__main__":
    transport = os.getenv("FASTMCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
