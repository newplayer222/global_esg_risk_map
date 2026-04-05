import pytest
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_verify_user():
    """测试用户验证功能"""
    from web.verify_user import verify_user

    # 这是一个基本的测试，需要根据实际数据调整
    # 这里只是示例，实际测试需要mock数据文件
    assert callable(verify_user)

def test_app_creation():
    """测试Flask应用创建"""
    from web.app import app

    assert app is not None
    assert hasattr(app, 'route')

def test_health_endpoint():
    """测试健康检查端点"""
    from web.app import app

    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'