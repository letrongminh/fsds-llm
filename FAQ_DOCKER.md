# Hướng dẫn Cập nhật FAQ với Docker

## Cấu trúc thư mục
```
.
├── docker-compose.yml    # Cấu hình Docker Compose
├── Dockerfile           # Cấu hình image Python
├── entrypoint.sh       # Script khởi động container
└── src/
    ├── utils/
    │   └── faq/
    │       ├── faq.json               # File FAQ gốc
    │       ├── faq_enriched.json      # File FAQ sau khi làm giàu
    │       ├── enrich_faq.py         # Script làm giàu FAQ
    │       └── add_document_to_pgvector.py  # Script thêm vào vector DB
    └── vectordb/
        └── init.sql    # File khởi tạo DB
```

## Yêu cầu
- Docker và Docker Compose
- File `.env` chứa OPENAI_API_KEY

## Cấu hình Docker
Hệ thống sử dụng hai services chính:

1. **postgres**:
   - Image: tensorchord/vchord-postgres:pg17-v0.1.0
   - Cung cấp PostgreSQL với pgvector extension
   - Data được persist qua volume postgres_data

2. **faq_processor**:
   - Build từ Dockerfile local
   - Xử lý việc làm giàu FAQ và thêm vào vector database
   - Kết nối tự động với PostgreSQL

## Cách sử dụng

1. Tạo file `.env` với nội dung:
```
OPENAI_API_KEY=your_api_key_here
```

2. Cập nhật file FAQ:
- Đặt file FAQ mới vào `src/utils/faq/faq.json`

3. Khởi động hệ thống:
```bash
docker-compose up --build
```

Quá trình sẽ tự động:
- Khởi động PostgreSQL với pgvector extension
- Chờ database sẵn sàng
- Tạo embedding và làm giàu FAQ data
- Thêm dữ liệu vào vector database

## Kiểm tra logs
```bash
# Xem logs của FAQ processor
docker-compose logs faq_processor

# Xem logs của PostgreSQL
docker-compose logs postgres
```

## Dọn dẹp
```bash
# Dừng và xóa containers
docker-compose down

# Xóa cả volume data (cẩn thận khi dùng)
docker-compose down -v
```

## Lưu ý

- Vector database được persist qua Docker volume postgres_data
- Hệ thống sử dụng cùng image và cấu hình với môi trường development
- Mỗi lần chạy sẽ làm giàu FAQ data và thêm vào DB
- Nếu muốn xóa dữ liệu cũ, sử dụng flag `-v` khi down
