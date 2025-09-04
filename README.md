# tabular-mcp

MCP Server that enables agents to work with tabular data contained within CSV and Excel files.

## Overview

The server provides secure execution of Python code in a sandboxed environment with data science libraries pre-installed. Data files are stored in a `./data` directory and must be loaded manually by the consumer.

### Tools

- **`list_data_files`** - Lists all CSV and Excel files in the data directory
- **`list_sheets`** - Lists all sheets in an Excel file with dimensions
- **`run_python_code`** - Executes Python code in a secure sandbox with pandas, numpy, matplotlib, and openpyxl
- **`list_available_python_libs`** - Shows available libraries in the sandbox environment

## Usage

1. Add CSV or Excel files to the `./data` directory
2. Use `list_data_files` to see available files
3. Use `run_python_code` to execute Python code - you'll need to load files manually:
   ```python
   import pandas as pd
   df = pd.read_csv('./data/your_file.csv')
   print(df.head())
   ```

## Example

Here's example code that an agent might generate to explore a CSV file:

```python
import pandas as pd

# Load the CSV file
df = pd.read_csv('./data/sample_sales.csv')

# Display basic information about the dataset
print(df.head())
print(f"\nDataset shape: {df.shape}")
print(f"\nColumn names: {list(df.columns)}")
```

This demonstrates the typical workflow: load data with pandas, then explore its structure and contents.

## Running

### Stdio Mode (Default)
```bash
uv run python main.py
```

### SSE Mode (HTTP Server)
```bash
# Set environment variables for SSE mode
export FASTMCP_TRANSPORT=sse
export FASTMCP_HOST=127.0.0.1  # optional, defaults to 127.0.0.1
export FASTMCP_PORT=8000       # optional, defaults to 8000

uv run python main.py
```

### Docker
```bash
# Stdio mode
docker run --rm -v ./data:/app/data tabular-mcp

# SSE mode
docker run --rm -p 8000:8000 -v ./data:/app/data \
  -e FASTMCP_TRANSPORT=sse \
  tabular-mcp
```

## Dependencies

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP)
- [MCP Run Python](https://github.com/pydantic/mcp-run-python) (code sandbox)

