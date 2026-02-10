"""
重置数据库脚本
删除旧数据库并创建新的数据库结构
"""
import os
import sys

# 设置 UTF-8 编码
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

# 数据库文件路径
DB_FILE = "neotrade.db"

def reset_database():
    """重置数据库"""
    # 检查数据库文件是否存在
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"✓ 已删除旧数据库文件: {DB_FILE}")
        except PermissionError:
            print(f"✕ 无法删除数据库文件，可能正在被使用")
            print("  请先停止应用，然后重试")
            return False
        except Exception as e:
            print(f"✕ 删除数据库失败: {e}")
            return False
    else:
        print(f"ℹ 数据库文件不存在，将创建新数据库")

    # 导入数据库模块
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
