import os
import sys
import subprocess

# 自动定位并切换到项目根目录（global_esg_risk_map/）
def setup_project_root():
    script_path = os.path.abspath(sys.argv[0] if __name__ == "__main__" else __file__)
    current_dir = os.path.dirname(script_path)
    for _ in range(10):
        if (os.path.isdir(os.path.join(current_dir, 'data')) and 
            os.path.isdir(os.path.join(current_dir, 'src'))):
            os.chdir(current_dir)
            return
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    raise RuntimeError("无法定位项目根目录！请确保脚本位于 global_esg_risk_map/ 目录结构中。")

# 执行设置
setup_project_root()


STEPS = {
    "1": {
        "name": "生成政策链接",
        "script": "src/pipeline/generate_policy_links.py",
        "desc": "调用大模型生成新的政策法规链接"
    },
    "2": {
        "name": "分析政策内容",
        "script": "src/pipeline/policy_content_analyse.py",
        "desc": "调用大模型分析政策原文，提取关键信息"
    },
    "3": {
        "name": "评估政策风险",
        "script": "src/pipeline/policy_risk_assessment.py",
        "desc": "调用大模型对政策进行五维风险打分"
    },
    "4": {
        "name": "计算政策总风险",
        "script": "src/pipeline/policy_total_risk_calculator.py",
        "desc": "根据行业相关性计算每条政策的加权风险"
    },
    "5": {
        "name": "汇总总风险",
        "script": "src/pipeline/total_risk_aggregator.py",
        "desc": "按国家-议题-行业维度汇总最终风险值"
    },
    "6": {
        "name": "生成最终地图",
        "script": "src/pipeline/generate_global_esg_risk_map.py",
        "desc": "将风险数据渲染成交互式 HTML 地图"
    }
}

def run_script(script_name):
    """运行单个 Python 脚本，并检查是否成功"""
    print(f"\n🚀 正在执行: {script_name}")
    print("-" * 50)
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {script_name} 执行成功!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 执行失败! 错误码: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ 找不到脚本文件: {script_name}")
        return False

def display_menu():
    """显示操作菜单"""
    print("\n" + "="*60)
    print("🛠️  ESG 风险地图生成流程 - 交互式选择")
    print("="*60)
    for key, step in STEPS.items():
        print(f"{key}. {step['name']}")
        print(f"   -> {step['desc']}")
    print("q. 退出程序")
    print("-"*60)

def main():
    print("🌍 欢迎使用 ESG 风险地图生成工具！")
    
    while True:
        display_menu()
        choice = input("请选择要执行的步骤编号 (1-6) 或输入 'q' 退出: ").strip().lower()

        if choice == 'q':
            print("👋 再见！")
            break
        elif choice in STEPS:
            success = run_script(STEPS[choice]["script"])
            if not success:
                retry = input("是否要重试此步骤？(y/n): ").strip().lower()
                if retry != 'y':
                    continue
        else:
            print("❌ 无效的选择，请输入 1-6 之间的数字或 'q'。")

if __name__ == "__main__":
    main()
