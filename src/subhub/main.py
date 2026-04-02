"""SubHub 主入口。启动对话循环和提醒线程。"""

import sys
import threading
from pathlib import Path
from datetime import date

from subhub.config import load_config
from subhub.store import SubscriptionStore
from subhub.chat import ChatSession
from subhub.reminder import ReminderThread, check_reminders


_print_lock = threading.Lock()


def reminder_output(text: str):
    """提醒线程的输出回调，线程安全地打印到终端。"""
    with _print_lock:
        print(f"\n{'=' * 50}")
        print(text)
        print(f"{'=' * 50}\n")


def main():
    config_path = Path("config.toml")
    env_path = Path(".env")

    if not config_path.exists():
        print("❌ 未找到 config.toml，请确保在项目目录下运行")
        sys.exit(1)

    config = load_config(str(config_path), str(env_path))
    store = SubscriptionStore(config.data.filepath)

    # 启动后台提醒线程
    reminder = ReminderThread(
        store=store, advance_days=config.reminder.advance_days,
        check_interval_hours=config.reminder.check_interval_hours,
        output_callback=reminder_output,
        base_currency=config.report.base_currency,
    )
    reminder.start()

    session = ChatSession(config.llm, store,
                           base_currency=config.report.base_currency)

    print("🔔 SubHub 订阅管理助手已启动")
    print(f"📂 数据文件：{config.data.filepath}")
    print(f"⏰ 提醒：提前 {config.reminder.advance_days} 天，"
          f"每 {config.reminder.check_interval_hours} 小时检查")
    print("💬 输入消息开始对话，输入 'quit' 或 'exit' 退出\n")

    # 启动时立即检查一次
    startup_reminder = check_reminders(store, date.today(), config.reminder.advance_days)
    if startup_reminder:
        reminder_output(startup_reminder)

    while True:
        try:
            user_input = input("你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "退出"):
                print("👋 再见！")
                reminder.stop()
                break
            reply = session.chat(user_input)
            with _print_lock:
                print(f"\n助手: {reply}\n")
        except KeyboardInterrupt:
            print("\n👋 再见！")
            reminder.stop()
            break
        except Exception as e:
            print(f"\n❌ 发生错误：{e}\n")


if __name__ == "__main__":
    main()
