---
type: Runbook
title: Run app and refresh data
description: Start backend/frontend; run pipeline steps in order.
tags: [ops]
timestamp: 2026-10-18T20:00:00Z
---

```bash
Backend/.venv/bin/uvicorn app.main:app --port 8000 --app-dir Backend   # แก้โค้ดแล้วต้อง restart
cd frontend && npm run dev                                             # พอร์ต 3001
```

รันจาก `Backend/` ตามลำดับ:
```bash
.venv/bin/python -m pipeline.ingest   # ราคา ~90 วิ
.venv/bin/python -m pipeline.rank     # แทนที่ recommendations ทั้งหมด
.venv/bin/python -m pipeline.news     # --all = 503 ตัว ~9 นาที
.venv/bin/python -m pipeline.analyze  # Laya: ต้องมี LAYA_URL/LAYA_TOKEN
.venv/bin/python -m pipeline.llm      # ~9 วิ/ตัว: ต้องมี LLM_URL/LLM_TOKEN
```
ต้องรัน news/analyze/llm **หลัง rank ทุกครั้ง** (`llm_analysis` เก็บแถวเก่า API ใช้แถวสำเร็จล่าสุดต่อ ticker)
ข่าวสะสมเฉพาะเมื่อรัน `news` สม่ำเสมอ (Google News เก็บ ~7 วัน) · ติดตั้ง cron ต้อง **ถามผู้ใช้ก่อน**
