"""
重置数据库脚本
重置 PostgreSQL 数据库结构
"""
import sys

# 设置 UTF-8 编码
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def reset_database():
    """重置数据库"""
    try:
        from backend.core.database import init_db
        print("✓ 正在创建新数据库...")
        init_db()
        print("✓ 数据库初始化完成！")

        # 初始化默认数据
        from backend.utils.init_prompts import init_prompts
        print("✓ 正在初始化 AI 策略...")
        init_prompts()
        print("✓ AI 策略初始化完成！")

        print("\n🎉 数据库重置成功！现在可以启动应用了。")
        return True
    except Exception as e:
        print(f"✕ 初始化数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("CryptoMindSim - 数据库重置工具")
    print("=" * 50)
    print("\n⚠️  警告：此操作将删除所有现有数据！")

    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        # 强制执行，不需要确认
        reset_database()
    else:
        # 需要用户确认
        confirm = input("\n是否继续？(输入 yes 确认): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("已取消操作")
