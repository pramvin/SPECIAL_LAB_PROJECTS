---
type: Tech Context
title: Tech stack and cautions
description: Stack, ports, environment rules. Commands live in runbooks/.
tags: [tech]
timestamp: 2026-10-18T20:00:00Z
---

- **Frontend:** Next.js **v16** (breaking changes: อ่าน `frontend/node_modules/next/dist/docs/` ก่อนเขียน) + React + TS · พอร์ต **3001** (3000 = Colony ของผู้ใช้)
- **Backend:** Python 3.14, FastAPI, uvicorn, yfinance, pandas, lxml, requests · พอร์ต 8000 · SQLite `Backend/planwise.db`
- **ข้อมูล:** ราคา yfinance (2 ปี), ข่าว Google News RSS (~7 วัน)
- **AI:** Laya + Ollama `qwen3:8b` บน Kaggle T4 x2
- คำสั่ง: [daily-refresh](runbooks/daily-refresh.md), [kaggle-gateways](runbooks/kaggle-gateways.md)

## ข้อควรระวัง
- **ห้ามติดตั้ง torch/transformers/laya บนเครื่องผู้ใช้**
- `Backend/.env` เป็นความลับ: ห้ามพิมพ์เนื้อหา · **ห้ามเดา token ทีละตัวอักษร** (ถูกบล็อกเป็น credential guessing)
- ทดสอบกับสำเนา DB (`PLANWISE_DB=/path/copy.db`) + พอร์ตชั่วคราว · backend ไม่มี `--reload` · macOS ไม่มี `timeout`
- อย่าแตะ Kaggle notebook `colony-models-eval` และ process ของผู้ใช้ (:8000, :3000, :3001)
