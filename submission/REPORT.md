# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm baseline `validate_logs.py` (CP0): 30/100
- Điểm cuối `validate_logs.py`: 100/100
- Tổng số traces:
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `config/dashboard.yaml`

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: `v1` / `baseline`
- Version/label candidate: `v2` / `candidate`
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel
- Evidence dashboard: `submission/evidence/`
- SLO đã chọn và lý do: `config/slo.yaml` (Latency P95 <= 3000ms, Error rate <= 2%, Cost <= $2.50)
- Alert rules và runbook: `config/alert_rules.yaml` và `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Đinh Lê Hoàng Danh | Metrics, Traces, Dashboard (6 panel), SLO & Alert Rules / Runbook | Branch `hoangdanh` | Cách xây dựng SLO/Alerts, dựng contract Dashboard 6 panel và validate log context |
| | | | |
