#!/bin/bash
# Quick Virtual Environment Checker for Analyst Agent

echo "🔍 Virtual Environment Status Check"
echo "=================================="

# Check if in virtual environment
if [[ "$VIRTUAL_ENV" ]]; then
    echo "✅ Virtual Environment: Active"
    echo "   Path: $VIRTUAL_ENV"
    echo "   Python: $(which python)"
else
    echo "⚠️  Virtual Environment: Not active"
    echo "   Global Python: $(which python)"
fi

echo ""
echo "🐍 Python Version: $(python --version)"

# Check pip version
echo "📦 Pip Version: $(pip --version | cut -d' ' -f2)"

echo ""
echo "🧪 Quick Package Check:"
echo "----------------------"

# Core packages quick check
packages=("fastapi" "langchain" "pandas" "uvicorn" "pydantic")
for pkg in "${packages[@]}"; do
    if python -c "import $pkg" 2>/dev/null; then
        version=$(python -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>/dev/null)
        echo "✅ $pkg ($version)"
    else
        echo "❌ $pkg (not installed)"
    fi
done

echo ""
echo "💡 For detailed dependency check, run:"
echo "   python check_dependencies.py" 