# tabular-data-mcp

MCP Server that enables agents to work with tabular data contained within CSV and Excel files.

⚠️ **SANDBOXED**: This server attempts to execute Python code in a restricted environment using RestrictedPython. While this provides some isolation, it should not be considered fully secure.

## Overview

The server provides sandboxed execution of Python code with data science libraries available. Code is executed in a restricted environment that attempts to limit access to system functions, file system operations outside the data directory, and unauthorized imports. Data files are stored in a `./data` directory and must be loaded manually by the consumer.

### Tools

- **`list_data_files`** - Lists all CSV and Excel files in the data directory
- **`list_sheets`** - Lists all sheets in an Excel file with dimensions
- **`run_python_code`** - Executes Python code in a sandboxed environment with pandas, numpy, matplotlib, and openpyxl
- **`list_available_python_libs`** - Shows available libraries in the execution environment

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

### Environment Variables

- `FASTMCP_TRANSPORT`: Transport mode (`stdio` or `sse`, defaults to `stdio`)
- `FASTMCP_HOST`: Host for SSE mode (defaults to `127.0.0.1`)
- `FASTMCP_PORT`: Port for SSE mode (defaults to `8000`)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, defaults to `INFO`)
  - Set to `DEBUG` to see detailed logging including the Python code being executed

### Docker
```bash
# Stdio mode
docker run --rm -v ./data:/app/data tabular-data-mcp

# SSE mode
docker run --rm -p 8000:8000 -v ./data:/app/data \
  -e FASTMCP_TRANSPORT=sse \
  tabular-data-mcp
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

Here's another example showing how an agent might work with an Excel file:

```python
import pandas as pd

# Load an Excel file with multiple sheets
excel_file = './data/sample_sales.xlsx'

# Read a specific sheet
df = pd.read_excel(excel_file, sheet_name='sample_sales')

# Display summary statistics for numerical columns
print(df.describe())
print(f"\nMissing values:\n{df.isnull().sum()}")

# Calculate total revenue (quantity * price)
df['revenue'] = df['quantity'] * df['price']

# Group by category and calculate sales metrics
category_summary = df.groupby('category').agg({
    'revenue': ['sum', 'mean'],
    'quantity': 'sum',
    'product': 'count'
}).round(2)
print(f"\nSales by Category:\n{category_summary}")

# Top performing salesperson
salesperson_performance = df.groupby('salesperson')['revenue'].sum().sort_values(ascending=False)
print(f"\nTop Salesperson:\n{salesperson_performance.head()}")
```

## Sample AutoGen Agent

A sample AutoGen agent (`sample_autogen_agent.py`) is included that demonstrates how to use this MCP server with Microsoft's AutoGen framework. The agent connects to the server running in SSE mode and can analyze tabular data through natural language commands.

To use the sample agent:

1. Start the MCP server in SSE mode:
   ```bash
   export FASTMCP_TRANSPORT=sse
   uv run python main.py
   ```

2. Run the AutoGen agent with a task:
   ```bash
   python sample_autogen_agent.py "Analyze the sales data and show me the top 5 products by revenue"
   ```

The agent uses the MCP workbench to access the server's tools and can perform complex data analysis tasks through conversational commands.

## Sandboxing Features

The server uses RestrictedPython to provide a sandboxed execution environment with some restrictions:

- **Restricted Imports**: Attempts to only allow whitelisted modules (pandas, numpy, matplotlib, etc.)
- **File System Restrictions**: Tries to limit file access to the `./data` directory
- **System Command Filtering**: Attempts to prevent execution of system commands, subprocess calls, etc.
- **Function Filtering**: Tries to block access to `eval`, `exec`, `compile`, and other potentially dangerous functions
- **Import Control**: Uses a custom `__import__` function that attempts to only allow data science-related modules

### What's Intended to be Blocked

- `os.system()`, `subprocess` calls
- File access outside `./data` directory  
- Network operations
- Dangerous built-ins like `eval`, `exec`
- Unauthorized module imports
- System introspection functions

**Note**: These restrictions are best-effort and may not prevent all potential security issues. This sandboxing should not be relied upon for security-critical applications.

## Dependencies

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP)
- pandas, numpy, matplotlib, openpyxl (data science libraries)

