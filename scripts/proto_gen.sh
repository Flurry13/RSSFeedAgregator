#!/bin/bash

# gRPC Protocol Buffer Code Generation Script
# Generates Go and Python stubs from .proto files

set -e

echo "🔧 Generating gRPC stubs from Protocol Buffers..."

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc not found. Please install Protocol Buffers compiler."
    echo "   Visit: https://protobuf.dev/getting-started/"
    exit 1
fi

# Directories
PROTO_DIR="shared/proto"
GO_OUT_DIR="services/api_go/internal/grpc/proto"
PYTHON_OUT_DIR="services/nlp_py/protogen"

# Create output directories
mkdir -p $GO_OUT_DIR
mkdir -p $PYTHON_OUT_DIR

echo "📁 Output directories:"
echo "   Go: $GO_OUT_DIR"
echo "   Python: $PYTHON_OUT_DIR"

# Generate Go stubs
echo "🔄 Generating Go gRPC stubs..."
protoc \
    --proto_path=$PROTO_DIR \
    --go_out=$GO_OUT_DIR \
    --go_opt=paths=source_relative \
    --go-grpc_out=$GO_OUT_DIR \
    --go-grpc_opt=paths=source_relative \
    $PROTO_DIR/*.proto

# Generate Python stubs
echo "🔄 Generating Python gRPC stubs..."
protoc \
    --proto_path=$PROTO_DIR \
    --python_out=$PYTHON_OUT_DIR \
    --grpc_python_out=$PYTHON_OUT_DIR \
    $PROTO_DIR/*.proto

# Create __init__.py files for Python package
touch $PYTHON_OUT_DIR/__init__.py

echo "✅ gRPC code generation completed!"
echo ""
echo "📊 Generated files:"
echo "   Go:"
find $GO_OUT_DIR -name "*.go" -type f | head -10
echo "   Python:"
find $PYTHON_OUT_DIR -name "*.py" -type f | head -10

echo ""
echo "🎯 Next steps:"
echo "   1. Update Go imports in services/api_go"
echo "   2. Update Python imports in services/nlp_py" 
echo "   3. Implement gRPC client/server logic" 