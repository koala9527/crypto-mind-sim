"""
测试用户注销功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_delete_user():
    """测试注销用户功能"""
    print("=" * 60)
    print("测试用户注销功能")
    print("=" * 60)

    # 1. 注册测试用户
    print("\n步骤1: 注册测试用户...")
    register_data = {
        "username": "test_delete_user",
        "password": "test123"
    }

    response = requests.post(f"{BASE_URL}/api/register", json=register_data)
    if response.status_code == 201:
        user = response.json()
        user_id = user['id']
        print(f"✓ 用户注册成功: {user['username']} (ID: {user_id})")
    else:
        print(f"✗ 注册失败: {response.text}")
        return

    # 2. 创建一些数据（持仓、交易等）
    print(f"\n步骤2: 为用户创建测试数据...")

    # 创建持仓
    position_data = {
        "side": "LONG",
        "leverage": 5,
        "quantity": 0.01
    }
    response = requests.post(
        f"{BASE_URL}/api/users/{user_id}/positions",
        json=position_data
    )
    if response.status_code == 201:
        print("✓ 持仓创建成功")
    else:
        print(f"✗ 持仓创建失败: {response.text}")

    # 3. 查询用户数据
    print(f"\n步骤3: 查询用户数据...")
    response = requests.get(f"{BASE_URL}/api/users/{user_id}")
    if response.ok:
        user_data = response.json()
        print(f"✓ 用户信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")

    response = requests.get(f"{BASE_URL}/api/users/{user_id}/positions")
    if response.ok:
        positions = response.json()
        print(f"✓ 持仓数量: {len(positions)}")

    # 4. 删除用户
    print(f"\n步骤4: 注销用户账号...")
    response = requests.delete(f"{BASE_URL}/api/users/{user_id}")
    if response.ok:
        result = response.json()
        print(f"✓ 账号注销成功!")
        print(f"  返回信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"✗ 注销失败: {response.text}")
        return

    # 5. 验证用户已被删除
    print(f"\n步骤5: 验证用户是否已删除...")
    response = requests.get(f"{BASE_URL}/api/users/{user_id}")
    if response.status_code == 404:
        print("✓ 用户已被成功删除（返回404）")
    else:
        print(f"✗ 用户仍然存在: {response.status_code}")

    # 6. 验证关联数据已被删除
    print(f"\n步骤6: 验证关联数据是否已删除...")
    response = requests.get(f"{BASE_URL}/api/users/{user_id}/positions")
    if response.status_code == 404:
        print("✓ 持仓数据已被删除（返回404）")
    else:
        print(f"✗ 持仓数据仍然存在")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


def test_delete_with_conversations():
    """测试删除有对话记录的用户"""
    print("\n" + "=" * 60)
    print("测试删除有AI对话记录的用户")
    print("=" * 60)

    # 1. 注册用户
    print("\n步骤1: 注册用户...")
    register_data = {
        "username": "test_delete_with_ai",
        "password": "test123"
    }
    response = requests.post(f"{BASE_URL}/api/register", json=register_data)
    if response.status_code == 201:
        user = response.json()
        user_id = user['id']
        print(f"✓ 用户注册成功: ID {user_id}")
    else:
        print(f"✗ 注册失败")
        return

    # 2. 创建AI对话
    print(f"\n步骤2: 创建AI对话记录...")
    conversation_data = {
        "content": "当前市场趋势如何？"
    }
    response = requests.post(
        f"{BASE_URL}/api/users/{user_id}/conversations",
        json=conversation_data
    )
    if response.status_code == 201:
        print("✓ AI对话创建成功")
    else:
        print(f"✗ 对话创建失败")

    # 3. 删除用户
    print(f"\n步骤3: 注销用户...")
    response = requests.delete(f"{BASE_URL}/api/users/{user_id}")
    if response.ok:
        print("✓ 用户注销成功（包括AI对话记录）")
    else:
        print(f"✗ 注销失败: {response.text}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        # 测试1: 基本删除功能
        test_delete_user()

        # 测试2: 删除包含AI数据的用户
        test_delete_with_conversations()

    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
