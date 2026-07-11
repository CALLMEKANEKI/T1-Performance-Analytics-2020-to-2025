import os
from dotenv import load_dotenv
from app.agents import TextToSQLAgent

load_dotenv()

agent = TextToSQLAgent(
    db_url=os.getenv("DATABASE_URL"),
)

result = agent.ask("Top 5 champion T1 pick nhiều nhất năm 2023?")

# Sửa đoạn print này để kiểm tra trạng thái chạy
print("=== TRẠNG THÁI CHẠY ===")
print(f"Thành công: {result['success']}")
if not result['success']:
    print(f"Chi tiết lỗi bị ẩn: {result['error']}")

print("\n=== KẾT QUẢ ===")
print("SQL sinh ra:", result["sql"])
print("Câu trả lời:", result["answer"])