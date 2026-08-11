# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: **ParkNoTech**
- Khóa / Lớp: **K3**
- Repository URL: `https://github.com/dlhdwan/Day13-K3-parknotech`
- Commit SHA cuối: `duong-01695-prod-verified`
- Thành viên và vai trò:
  1. **Nguyễn Văn Hiếu** (MSSV: `2A202601831`) — Thành viên A (Logging & Middleware): Phụ trách **CP1** (Middleware, Correlation ID, và gán log metadata).
  2. **Đỗ Ngọc Anh** (MSSV: `2A202601343`) — Thành viên B (Security & Compliance): Phụ trách **CP1** (Uncomment processor, cấu hình regex patterns che PII và nâng cấp che PII toàn cục).
  3. **Đinh Lê Hoàng Danh** (MSSV: `2A202601890`) — Thành viên C (Metrics & Alerting): Phụ trách **CP2** (Tích hợp Langfuse, đo đếm `error_rate_pct`, viết SLO, Alert rules và Runbook).
  4. **Lưu Nhân Triệu Dương** (MSSV: `2A202601695`) — Thành viên D (QA & Incident Analyst): Phụ trách **CP3 & Báo cáo** (Chạy load test sinh dữ liệu, thiết kế Dashboard Spec, chủ trì điều tra Challenge CP3 và viết báo cáo `REPORT.md`).

---

## 2. Kết quả kỹ thuật

- Điểm baseline `validate_logs.py` (CP0): **30/100**
- Điểm cuối `validate_logs.py`: **100/100**
- Tổng số traces: **15** (10 baseline traces + 5 challenge traces)
- Số PII leak còn lại: **0**
- Link/đường dẫn dashboard: `config/dashboard.yaml`

---

## 3. Logging và tracing

- **Evidence correlation ID**: `submission/evidence/cp1-correlation-redaction.png`
  - *Mô tả*: Mỗi request HTTP đi vào API được gán một `correlation_id` duy nhất qua `CorrelationIdMiddleware`, lưu vào `structlog.contextvars`, xuất hiện trong mọi log line liên quan (`request_received`, `response_sent`, `request_failed`) và trả về client qua header `x-request-id`.
- **Evidence PII redaction**: `submission/evidence/cp1-correlation-redaction.png`
  - *Mô tả*: Toàn bộ chuỗi chứa email, số điện thoại Việt Nam (`+84` / `09x`), CCCD (12 số), thẻ tín dụng (16 số), hộ chiếu và địa chỉ đều được lọc đệ quy qua `scrub_event` thành `[REDACTED_*]` trước khi serialize JSON; đồng thời `user_id` được hash SHA-256 (`user_id_hash`).
- **Evidence trace waterfall**: `submission/evidence/p0-langfuse-traces.png`
  - *Mô tả*: Trực quan hóa cây thực thi gồm span `retrieve` (truy xuất tri thức từ Vector Corpus) và span `generation` (sinh phản hồi AI từ mô hình), ghi nhận chi tiết latency, input/output tokens và chi phí USD.
- **Giải thích một span đáng chú ý**:
  - Span `retrieve` trong hàm `app.mock_rag.retrieve`: Ở trạng thái bình thường, span này phản hồi tức thời (<1ms); khi kích hoạt sự cố `rag_slow`, span kéo dài **2500ms**, chiếm đến **94.3%** tổng latency của request, giúp khoanh vùng chính xác điểm nghẽn nằm ở tầng retrieval chứ không phải ở LLM generation.

---

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `v1` / `baseline` (và nhãn `production` ban đầu)
- Version/label candidate: `v2` / `candidate`
- Trace ID của mỗi version:
  - Baseline (`v1` / `baseline`): `tr-lf-v1-4f81c9b2`
  - Candidate (`v2` / `candidate`): `tr-lf-v2-8a93e10d`
- **Bằng chứng đổi label hoặc rollback**: `submission/evidence/p0-langfuse-traces.png`
  - *Mô tả quy trình*: Hệ thống hỗ trợ chuyển nhãn `production` từ `v1` sang `v2` trên giao diện Langfuse Prompt Management. Khi phát hiện candidate v2 có dấu hiệu tăng độ trễ hoặc token cost, nhóm thực hiện rollback nhãn `production` về lại `v1` ngay lập tức mà không cần sửa code hay redeploy dịch vụ.

---

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
- Evidence dashboard: `submission/evidence/cp1-validator-100.png` (cùng contract chuẩn tại `config/dashboard.yaml`)
  1. **Latency Panel**: Đo lường phân vị P50, P95, P99 từ `response_sent.latency_ms` (Threshold: P95 $\le$ 3000ms).
  2. **Traffic Panel**: Đếm số request theo phút từ `request_received` (Threshold: $\ge$ 1 req/min).
  3. **Errors Panel**: Tỷ lệ lỗi % và phân loại theo `error_type` từ `request_failed` (Threshold: $\le$ 2%).
  4. **Cost Panel**: Tổng chi phí USD tích lũy và theo phút từ `response_sent.cost_usd` (Threshold: $\le$ $2.50).
  5. **Tokens Panel**: Tổng token input và output từ `response_sent.tokens_in/tokens_out` (Threshold: $\le$ 50,000 tokens).
  6. **Quality Panel**: Điểm đánh giá chất lượng phản hồi trung bình từ `response_sent.quality_score` (Threshold: $\ge$ 0.75).
- **SLO đã chọn và lý do**: `config/slo.yaml`
  - *Latency P95 $\le$ 3000ms (Target: 99.5%)*: Đảm bảo 99.5% tương tác người dùng có phản hồi nhanh, không bị timeout.
  - *Error Rate $\le$ 2% (Target: 99.0%)*: Duy trì độ sẵn sàng cao của dịch vụ API.
  - *Daily Cost $\le$ $2.50 (Target: 100%)*: Kiểm soát ngân sách vận hành token AI.
  - *Quality Score Avg $\ge$ 0.75 (Target: 95.0%)*: Đảm bảo chất lượng câu trả lời luôn đạt chuẩn ngữ cảnh.
- **Alert rules và runbook**: `config/alert_rules.yaml` và `docs/alerts.md`
  - Gồm 3 cảnh báo Symptom-based: `HighLatencyP95` (Critical), `HighErrorRate` (Critical), `HighDailyCost` (Warning) đi kèm 3 bước điều tra chuẩn và biện pháp mitigation trong Runbook.

---

## 6. Điều tra challenge

- **Challenge ID**: `day13-k3-observability-v1`
- **Triệu chứng từ metrics**: Panel Latency trên Dashboard ghi nhận độ trễ P95 tăng vọt từ ~150ms lên **2650ms** (vượt ngưỡng threshold cho phép 2000ms) khi hệ thống xử lý các truy vấn thuộc feature `refund`.
- **Trace ID liên quan**: `tr-challenge-k3-s01-7b9a`
- **Log line/correlation ID liên quan**: `correlation_id="req-challenge-s01"`, sự kiện `response_sent` ghi nhận `latency_ms=2650`, `feature="refund"`, `service="api"`.
- **Root cause**: Bước tra cứu tài liệu nghiệp vụ hoàn tiền trong hàm `retrieve()` (incident `rag_slow`) gặp tình trạng tắc nghẽn vector retrieval, gây delay cố định 2.5 giây cho mỗi truy vấn tìm kiếm tri thức hoàn tiền.
- **Fix action**:
  1. Tắt incident qua endpoint điều khiển: `POST /incidents/rag_slow/disable`.
  2. Trong môi trường production: Tối ưu index Vector DB, tăng kích thước connection pool và bật cache bộ nhớ cho các chính sách tra cứu phổ biến (`refund`, `policy`).
- **Preventive measure**:
  - Thiết lập **Timeout 1000ms** và **Circuit Breaker** cho tầng Vector Retrieval.
  - Xây dựng cơ chế fallback tự động sang Keyword Search (Lexical) khi Vector DB bị chậm.
  - Bổ sung metric riêng cho độ trễ từng span của Retrieval và LLM Call để cảnh báo sớm trước khi chạm ngưỡng SLO.

---

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | MSSV | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|---|
| **Nguyễn Văn Hiếu** | `2A202601831` | Cấu hình Middleware `CorrelationIdMiddleware`, liên kết `x-request-id`, quản lý contextvars và gán log metadata (`user_id_hash`, `session_id`, `feature`, `model`, `env`) | Branch `feature/logging-middleware` | Cách quản lý luồng contextvars an toàn trong ứng dụng bất đồng bộ FastAPI và xâu chuỗi log qua correlation ID. |
| **Đỗ Ngọc Anh** | `2A202601343` | Kích hoạt processor `scrub_event`, xây dựng regex patterns che PII (`email`, `phone_vn`, `cccd`, `credit_card`, `passport`, `address_vn`), nâng cấp che PII toàn cục đệ quy | Branch `feature/pii-security` | Nắm vững kỹ thuật scrub PII trước khi serialize JSON để triệt tiêu hoàn toàn nguy cơ rò rỉ thông tin cá nhân. |
| **Đinh Lê Hoàng Danh** | `2A202601890` | Tích hợp Langfuse SDK adapter, đo đếm metric `error_rate_pct` & `latency_ms`, soạn thảo SLO ([`config/slo.yaml`](file:///c:/Users/ADMIN/Desktop/Code%20Space/Day13-K3-parknotech/config/slo.yaml)), Alert rules ([`config/alert_rules.yaml`](file:///c:/Users/ADMIN/Desktop/Code%20Space/Day13-K3-parknotech/config/alert_rules.yaml)) và Runbook ([`docs/alerts.md`](file:///c:/Users/ADMIN/Desktop/Code%20Space/Day13-K3-parknotech/docs/alerts.md)) | Branch `feature/metrics-alerting` | Hiểu cách thiết lập các chỉ số định lượng SLI/SLO theo triệu chứng người dùng và xây dựng runbook giảm thiểu sự cố. |
| **Lưu Nhân Triệu Dương** | `2A202601695` | Thực thi load test sinh dữ liệu log, thiết kế Dashboard Spec 6 panels ([`config/dashboard.yaml`](file:///c:/Users/ADMIN/Desktop/Code%20Space/Day13-K3-parknotech/config/dashboard.yaml)), chủ trì điều tra Challenge (CP3) theo tam giác quan sát (Metrics $\rightarrow$ Traces $\rightarrow$ Logs) và hoàn thiện báo cáo `REPORT.md` | Branch `duong-01695-dev` | Làm chủ quy trình điều tra sự cố đa tầng, định vị root cause chính xác bằng correlation ID và trace waterfall. |
