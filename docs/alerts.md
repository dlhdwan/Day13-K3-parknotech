# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: Critical
- SLI/SLO liên quan: `latency_p95_ms <= 3000ms` (Target: 99.5%)
- Điều kiện và thời gian duy trì: Latency P95 > 3000ms kéo dài liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng chờ phản hồi từ AI lâu hoặc bị ngắt kết nối/timeout
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Latency trên Dashboard để xác nhận độ trễ tăng ở P95/P99.
  2. Mở Langfuse Traces, lọc các trace có duration > 3000ms để tìm span bị chậm (RAG retrieval hay LLM generation).
  3. Tra cứu log file `data/logs.jsonl` theo `correlation_id` của trace đó để kiểm tra lỗi hoặc nghẽn cổ chai.
- Mitigation tạm thời: Tắt incident/feature bị chậm hoặc rollback phiên bản prompt về baseline.
- Owner: Đinh Lê Hoàng Danh (Metrics & Alerting)

## Alert 2

- Tên: HighErrorRate
- Severity: Critical
- SLI/SLO liên quan: `error_rate_pct <= 2%` (Target: 99.0%)
- Điều kiện và thời gian duy trì: Tỷ lệ request lỗi (`request_failed`) > 2% kéo dài trong 5 phút
- Ảnh hưởng tới người dùng: Yêu cầu của người dùng bị từ chối với lỗi HTTP 500
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors & breakdown trên Dashboard để xác định loại `error_type`.
  2. Tra cứu sự kiện `request_failed` trong `data/logs.jsonl` để lấy danh sách `correlation_id` bị ảnh hưởng.
  3. Lọc traces lỗi trên Langfuse để xem chi tiết exception stacktrace.
- Mitigation tạm thời: Tắt incident đang bật (`POST /incidents/{name}/disable`) hoặc restart API server.
- Owner: Đinh Lê Hoàng Danh (Metrics & Alerting)

## Alert 3

- Tên: HighDailyCost
- Severity: Warning
- SLI/SLO liên quan: `daily_cost_usd <= 2.50 USD` (Target: 100%)
- Điều kiện và thời gian duy trì: Tổng chi phí USD tích lũy vượt $2.50 trong cửa sổ quan sát
- Ảnh hưởng tới người dùng: Vượt ngân sách vận hành hệ thống AI
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Cost over time và Tokens on Dashboard để tìm thời điểm chi phí tăng đột biến.
  2. Lọc các trace có `cost_usd` cao nhất trên Langfuse.
  3. Kiểm tra số lượng input/output tokens và model/prompt label đang được dùng.
- Mitigation tạm thời: Chuyển `LANGFUSE_PROMPT_LABEL` về phiên bản tiết kiệm token hoặc áp dụng rate-limit.
- Owner: Đinh Lê Hoàng Danh (Metrics & Alerting)
