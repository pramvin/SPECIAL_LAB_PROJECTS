---
type: Runbook
title: Start Laya + LLM on Kaggle
description: One notebook runs both gateways; steps, verification, gotchas.
tags: [ops, kaggle, ai]
timestamp: 2026-10-18T20:00:00Z
---

1. Kaggle (บัญชี `faislol`) → Import `Backend/experiments/kaggle_gateways.ipynb` · GPU **T4 x2**, Internet On
2. รัน cell 1 (setup) → 2 (เขียนไฟล์เซิร์ฟเวอร์) → 3 (launch **ปล่อยรันค้าง**; รันซ้ำได้ มันฆ่าตัวเก่าและออก token ใหม่)
3. Cell 3 พิมพ์ `LLM_URL LLM_TOKEN LAYA_URL LAYA_TOKEN` (token เดียว 2 URL) → ใส่ `Backend/.env`
4. ตรวจ: `curl <url>/health`; token ผิดต้อง 401; `pipeline.llm --limit 2` = end-to-end
5. เสร็จแล้ว **หยุด session** (ลิงก์อยู่ ≤ ~11 ชม.)

## Gotchas
- output อยู่ใน iframe อ่านเป็นข้อความไม่ได้; วิธีย้ายค่าที่ปลอดภัย: ผู้ใช้คัดลอก 4 บรรทัด หรือดาวน์โหลด `.ipynb` แล้วอ่านข้อความ · ภาพหน้าจอเสี่ยง `I`/`l` สับสน · **ห้ามเดา token**
- Ollama ต้องมี `zstd` + `pciutils` (notebook ติดตั้งให้) · Ollama GPU 0, Laya GPU 1
- เพิ่ม dataset ระหว่างรัน = session รีเซ็ต · "Run All" บางทีหยุดกลางทาง รัน cell ที่เหลือเอง
- Laya `/analyze` ถ้าข่าวทั้งหมดถูกให้คะแนนแล้ว `analyze` จะบอก "0 headlines" → ทดสอบโดย POST ตรง
- แก้ `laya_server/server.py` หรือ `llm_server/server.py` แล้วต้อง regenerate notebook
