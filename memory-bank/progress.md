---
type: Progress
title: Stage and task status
description: Status of the 8 pipeline stages, DB size, task list T0-T12.
tags: [status]
timestamp: 2026-10-30T06:22:20Z
---

สถานะ: ✅ Done · 🟡 Built, unvalidated · ⬜ Todo · ⏸ Deferred (ผู้ใช้เรียกเอง) · ❌ Dropped

| # | Stage | สถานะ | ไฟล์ |
|---|---|---|---|
| 0 | Prices | ✅ | `pipeline/ingest.py` |
| 1 | Earnings trigger | ⏸ | |
| 2 | Google News | ✅ | `pipeline/news.py` |
| 2 | SEC EDGAR | ⏸ | |
| 2 | X/influencer | ❌ | |
| 3 | Source check | ⬜ | |
| 4 | Laya filter | 🟡 ต้องเปลี่ยนเป็น event/rumor/filler | `laya_server/server.py`, `pipeline/analyze.py` |
| 5 | LLM analysis | 🟡 | `pipeline/llm.py`, `llm_server/server.py` |
| 6 | Risk/size (ATR) | ✅ | `pipeline/rank.py`, `app/main.py` |
| 7 | UI การ์ดไอเดีย | ✅ (บั๊กลิงก์ `ReasonText`) | `frontend/src/components/ideas/` |
| 8 | Backtest/event study | ⬜ | |

**DB:** universe 503 · prices 250,840 · recommendations 60 · news_items 12,801 (10-09..10-16) · llm_analysis 44 · news_scores 1,217 · data_issues 4

## Tasks
| ID | งาน | สถานะ |
|---|---|---|
| T0 | ผู้ใช้ติดป้าย `Backend/experiments/to_label.csv` 200 แถว | ⬜ รอผู้ใช้ |
| T1 | ประเมิน Laya/FinBERT/กฎ keyword กับป้าย | ⬜ หลัง T0 |
| T2 | Stage 3 source tier + corroboration | ⬜ |
| T3 | Stage 4 → event/rumor/filler + regenerate notebook | ⬜ |
| T4 | SEC EDGAR | ⏸ |
| T5 | LLM: rerun หลัง `rank`, ป้อนข่าวที่กรองแล้ว, ตรวจกับป้าย | 🟡 |
| T6 | UI: แทนชิป Laya, credibility badge, แก้ `ReasonText` | 🟡 |
| T7 | Earnings trigger + scheduler | ⏸ |
| T8 | Backtest, event study, latency (ระบุ survivorship bias) | ⬜ |
| T9 | รวมไฟล์ LLM-server ซ้ำ | ✅ ลบแล้ว 10-27 |
| T10 | ลบบัญชีทดสอบ + ตัดสินใจ `SocialSentiment` | ✅ แทน mock ด้วย `NewsSentiment` (Google News จริง); sentiment รอ scoring |
| T11 | ชั้นตัวเลขยืนยัน: เทียบป้าย Laya/LLM กับผลราคาจริง (ดู activeContext) | ⬜ รอผู้ใช้อนุมัติแผน |
| T12 | Per-stock sentiment questionnaire (backend) | 🟡 table + API พร้อม (`sentiment_responses`) · UI ลบตามคำสั่งผู้ใช้ 2026-10-30 |

ผลทดลอง: [experiments/results](experiments/results.md)
