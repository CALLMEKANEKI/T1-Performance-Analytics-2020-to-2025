from app.agents import TextToSQLAgent
from app.config import AppConfig

agent = TextToSQLAgent(db_url=AppConfig.DATABASE_URL)

result = agent.ask("Top 5 champion T1 pick nhiều nhất năm 2023?")

print("=== TRẠNG THÁI CHẠY ===")
print(f"Thành công: {result['success']}")
if not result["success"]:
    print(f"Chi tiết lỗi bị ẩn: {result['error']}")

print("\n=== KẾT QUẢ ===")
print("SQL sinh ra:", result["sql"])
print("Câu trả lời:", result["answer"])
