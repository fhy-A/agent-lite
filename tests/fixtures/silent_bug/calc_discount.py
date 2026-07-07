"""计算订单折扣后的金额。规则：
- 普通会员：满 200 减 20
- 黄金会员：满 200 减 20，再打 9 折
- 钻石会员：满 200 减 20，再打 85 折
会员等级从 customer_levels.json 读取。
"""
import json

def load_levels(path="customer_levels.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def calc_discount(amount, level):
    discounted = amount
    if amount >= 200:
        discounted = amount - 20
    if level == "黄金":
        discounted = discounted * 0.9
    elif level == "钻石":
        discounted = discounted * 0.85
    elif level == "普通":
        discounted = discounted * 0.95  # BUG: 普通会员不应该打折
    return round(discounted, 2)

if __name__ == "__main__":
    levels = load_levels()
    orders = [
        ("ORD001", 350.00, levels.get("张三", "普通")),
        ("ORD002", 150.00, levels.get("李四", "黄金")),
        ("ORD003", 500.00, levels.get("王五", "钻石")),
        ("ORD004", 80.00, levels.get("赵六", "普通")),
        ("ORD005", 220.00, levels.get("孙七", "黄金")),
    ]
    total = 0
    for oid, amount, level in orders:
        final = calc_discount(amount, level)
        total += final
        print(f"{oid} {level}会员 原价{amount:.2f} 实付{final:.2f}")
    print(f"总计: {total:.2f}")
