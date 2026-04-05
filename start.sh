#!/bin/bash

# Global ESG Risk Map 启动脚本

echo "🌍 Global ESG Risk Map 启动脚本"
echo "================================="

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装或不在PATH中"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "⚠️  未检测到虚拟环境，正在创建..."
    python -m venv venv
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 文件不存在"
    exit 1
fi

echo "📦 检查并安装依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，请创建并设置 DASHSCOPE_API_KEY"
    echo "创建 .env 文件示例："
    echo "DASHSCOPE_API_KEY=your_api_key_here"
    exit 1
fi

echo ""
echo "选择操作："
echo "1. 运行完整数据处理流水线"
echo "2. 启动Web应用"
echo "3. 运行流水线然后启动Web应用"
echo "4. 退出"

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo "🚀 运行完整数据处理流水线..."
        python src/run_all_pipeline.py
        ;;
    2)
        echo "🌐 启动Web应用..."
        python src/web/app.py
        ;;
    3)
        echo "🚀 运行流水线..."
        python src/run_all_pipeline.py
        echo ""
        echo "🌐 启动Web应用..."
        python src/web/app.py
        ;;
    4)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac