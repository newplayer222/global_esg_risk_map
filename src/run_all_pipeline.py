import os
import sys

# 自动定位并切换到项目根目录（global_esg_risk_map/）
def setup_project_root():
    # 获取当前脚本的绝对路径
    script_path = os.path.abspath(sys.argv[0] if __name__ == "__main__" else __file__)
    current_dir = os.path.dirname(script_path)
    
    # 向上查找，直到找到同时包含 'data' 和 'src' 的目录
    for _ in range(10):  # 最多向上找10层，防止无限循环
        if (os.path.isdir(os.path.join(current_dir, 'data')) and 
            os.path.isdir(os.path.join(current_dir, 'src'))):
            os.chdir(current_dir)
            return
        parent = os.path.dirname(current_dir)
        if parent == current_dir:  # 已到达文件系统根目录
            break
        current_dir = parent
    
    raise RuntimeError("无法定位项目根目录！请确保脚本位于 global_esg_risk_map/ 目录结构中。")

# 执行设置
setup_project_root()



# run_all_pipeline.py
"""
全自动运行整个 ESG 风险地图生成流程。
执行顺序:
1. generate_policy_links.py       -> 生成政策链接
2. policy_content_analyse.py      -> 分析政策内容
3. policy_risk_assessment.py      -> 评估政策风险
4. policy_total_risk_calculator.py-> 计算政策总风险
5. total_risk_aggregator.py       -> 汇总总风险
6. generate_global_esg_risk_map.py-> 生成最终地图
"""

import subprocess
import sys
import os

def run_script(script_name):
    """运行单个 Python 脚本，并检查是否成功"""
    print(f"\n🚀 正在执行: {script_name}")
    print("-" * 50)
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {script_name} 执行成功!\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 执行失败! 错误码: {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ 找不到脚本文件: {script_name}")
        sys.exit(1)

def main():
    print("🌍 开始全自动 ESG 风险地图生成流程...")
    print("=" * 60)

    scripts = [
        "src/pipeline/generate_policy_links.py",
        "src/pipeline/policy_content_analyse.py",
        "src/pipeline/policy_risk_assessment.py",
        "src/pipeline/policy_total_risk_calculator.py",
        "src/pipeline/total_risk_aggregator.py",
        "src/pipeline/generate_global_esg_risk_map.py"
    ]

    for script in scripts:
        run_script(script)

    print("=" * 60)
    print("🎉 全自动流程执行完毕！请查看 global_esg_risk_map.html")

if __name__ == "__main__":
    main()
