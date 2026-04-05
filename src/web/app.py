# app.py
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.web.verify_user import verify_user

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

template_dir = os.path.join(os.getcwd(), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'global_esg_risk_map'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form.get('account')
        code = request.form.get('code')
        if verify_user(account, code):
            session['user'] = account
            return redirect(url_for('map_page'))
        else:
            return render_template('login.html', error="账号或密码错误")
    return render_template('login.html')

@app.route('/map')
def map_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('global_esg_risk_map.html')  # ← 改成这样！
    
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

@app.route('/update_map')
def update_map():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        import subprocess
        result = subprocess.run([sys.executable, 'src/run_all_pipeline.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            flash('地图数据已更新！', 'success')
        else:
            flash(f'更新失败：{result.stderr}', 'error')
    except Exception as e:
        flash(f'更新出错：{str(e)}', 'error')
    return redirect(url_for('map_page'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"✅ 服务启动中... http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)  # 建议临时开 debug=True 查错
