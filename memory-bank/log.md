---
type: Log
title: Change log
description: Chronological changes to this memory bank. Newest first.
---

- 2026-10-30 เพิ่ม `NewsSentiment` (Google News จริง) แทน mock, fixed status bar + Refresh (local/UTC), `/api/data-status`, questionnaire backend, seed demo, ซ่อน dev indicator, คืน `/api` rewrites; ตรวจด้วย screenshots 320–1440
- 2026-10-30 ลบ UI questionnaire ("Your view") และ "Your saved views" ตามคำสั่งผู้ใช้ (คง backend)
- 2026-10-27 ลบไฟล์ LLM-server ซ้ำ 5 ไฟล์ + ลบส่วน README ซ้ำ · บันทึกแบ่งงานทีม · push main
- 2026-10-27 ทดสอบ FMP: key ใช้ได้ แต่แพ็กเกจไม่รวมรายชื่อ S&P 500 (402) → รายชื่อยังมาจาก Wikipedia · `ingest.py` ลอง FMP ก่อนแล้วถอยไป Wikipedia · เก็บ `FMP_API_KEY` ใน `Backend/.env`
- 2026-10-26 บันทึกแนวชั้นตัวเลขยืนยัน (T11) ใน activeContext/progress · แก้ frontend error: ลบ cache `.next` แล้วเปิด dev ใหม่ที่ :3001 (พอร์ต 3000 เป็นของโปรเจกต์ Colony)
- 2026-10-19 เพิ่ม `README.md` ที่ root (โปรเจกต์คืออะไร, รัน backend/frontend, ใช้ Kaggle)
- 2026-10-19 ผล A/B anon (ข้อ E) และ think ล้มเหลวเพราะ tunnel 524 (ข้อ F) → คง think ปิด ตามที่ผู้ใช้ตกลง
- 2026-10-18 เปิด Kaggle gateways ใหม่ (แพตช์ `think` ในเซลล์ + ทดสอบแล้ว: think=true ใช้ token มากกว่าเดิมหลายเท่า) อัปเดต `.env` แล้ว session ค้างอยู่ ต้องหยุดเมื่อเสร็จ
- 2026-10-18 เพิ่มโค้ดทดลอง (ยังไม่รันกับโมเดล): `llm_ab.py --arm filter|anon|think`, `disagree.py` (รายงาน Laya เห็นต่างจาก LLM, รันได้ไม่ต้องใช้ Kaggle), ตัวเลือก `think` ใน `llm_server/server.py` + `kaggle_gateways.ipynb` (ต้อง Import notebook ใหม่บน Kaggle)
- 2026-10-18 รัน A/B ของ LLM (ตัด filler ที่ Laya ติดป้าย vs ไม่ตัด) ด้วย `Backend/pipeline/llm_ab.py` → ดู experiments/results ข้อ D
- 2026-10-18 เพิ่ม `CLAUDE.md` ที่ root: กฎอ่าน memory bank ก่อนทำงาน และอัปเดตหลังจบงาน
- 2026-10-18 จัดโครงใหม่ตาม Open Knowledge Format: เพิ่ม index/log, frontmatter, แยก runbooks/ และ experiments/ ออกจากไฟล์หลักเพื่อลด context
- 2026-10-18 สร้าง memory bank ครั้งแรกจาก `PIPELINE_SPEC.md`
