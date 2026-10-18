---
type: Architecture
title: System patterns
description: Pipeline stages, design patterns, scoring rules.
tags: [architecture, pipeline]
timestamp: 2026-10-18T20:00:00Z
---

**โครง:** FastAPI + SQLite (โมดูลเดียว) · Next.js · AI แยกบน Kaggle เรียกผ่าน HTTPS

**Flow:** trigger(1) → scrape(2) → source check(3) → Laya filter(4) → LLM(5) → risk/size(6) → trade idea UI(7) → backtest(8) · สถานะแต่ละขั้น: [progress](progress.md)

## Patterns
- รันเป็นขั้น `python -m pipeline.<step>` · `rank` **ลบและสร้าง `recommendations` ใหม่** → รัน news/analyze/llm ตามหลังเสมอ ([runbook](runbooks/daily-refresh.md))
- ทุกการตัดสินใจ reproducible จาก SQL: `llm_analysis`, `news_scores`, `data_issues`
- Gateway บน Kaggle ใช้ Bearer token, bind 127.0.0.1, เปิดผ่าน Cloudflare quick tunnel
- LLM: บังคับ JSON schema (Ollama `format`) + ตรวจในโค้ด (confidence 0..1, id ที่อ้างต้องอยู่ใน input, ต้องอ้าง headline) + retry 1 ครั้ง · **display-only** (ถ้าปรับคะแนนภายหลัง ≤ ±10 หลัง stage 8 พิสูจน์)
- Auth: scrypt + httpOnly cookie `session` · Frontend proxy `/api/*` ด้วย Next `rewrites()` (`BACKEND_URL` ฝังตอน build)
- `app/seed.py` ใส่ตัวอย่าง 12 รายการเฉพาะเมื่อ `recommendations` ว่าง

## Scoring (`pipeline/rank.py`)
percentile ของ momentum, volume ratio, low-volatility ถ่วงน้ำหนักต่อ horizon · กรอง: สภาพคล่อง ≥ $50M/วัน, ราคา > SMA50 (+SMA200 สำหรับ 1m/3m), ไม่เกิน 25% เหนือ SMA50, ≤ 4 ตัว/sector · ATR stop/target: 1w 2x/3x, 1m 3x/5x, 3m 4.5x/8x
⚠ น้ำหนักและตัวคูณเป็น **ค่าเดา ยังไม่ backtest**
