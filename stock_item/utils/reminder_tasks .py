from App.models import Item

def send_reminders():
    """
    リマインダーが必要なアイテムに通知を送る。
    """
    items = Item.objects.filter(reminder=True)
    for item in items:
        if item.check_reminder_due():
            print(f"リマインダー: {item.name} の購入が必要です。")
            # 必要に応じてメールや通知処理を追加
