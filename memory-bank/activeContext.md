---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, next order of work. Update most often.
tags: [active]
timestamp: 2026-10-18T20:00:00Z
---

**โฟกัส:** Stage 5 (LLM) รันครั้งแรกแล้ว 42/42 → ต้องทำให้เชื่อถือได้: แก้บั๊ก UI, กวาดไฟล์ซ้ำ, ให้ผู้ใช้ติดป้ายเพื่อวัดความแม่น

## ปัญหาค้าง
1. `ReasonText` (`IdeasView.tsx`) ใส่ `[1]` ทุกลิงก์; id ที่ไม่อยู่ใน `cited_news_ids` เป็นเลขเปล่า
2. ป้าย Laya ดูผิดในเคสชัด (MA ข่าวดีได้ Bearish) · ยังไม่มี ground truth
3. LLM เอนเอียง bullish (up 36/down 2/none 6)
4. Laya กับ LLM ยังไม่ต่อกัน (LLM อ่านทุก headline ที่ `rule_noise=0`)
5. ไฟล์ LLM-server ซ้ำ: `llm_server/{proxy.py,build_notebook.py}`, `experiments/{ollama_server_kaggle.ipynb,llm_kaggle_one_cell.py,llm_server_kaggle.ipynb}` + README มี 2 ส่วน LLM → เหลือ `kaggle_gateways.ipynb` ทางเดียว
6. บัญชีทดสอบ `llmcheck@planwise.test` ใน DB ต้องลบ

## สถานะ runtime (ณ จบ session ก่อน)
- Kaggle `notebookdd09550bcb` เริ่ม ~23:40 วันที่ 10-17 ลิงก์ตายแล้ว ค่าใน `.env` เก่า → **หยุด session** ประหยัด GPU
- `npm run build` ยังไม่รันหลังแก้ล่าสุด
- Git: commit `18182bd` มีแล้ว (spec เดิมเขียนว่ายังไม่ commit = ล้าสมัย) · สถานะ: `D Agenda.docx` · อย่า commit ถ้าไม่สั่ง

## รอผู้ใช้ตัดสินใจ
1. เก็บ/ลบ mock `SocialSentiment` (มีลายน้ำ SAMPLE)
2. อนุมัติ source tier + กฎ corroboration (Proposal)
3. อนุมัติเกณฑ์ Laya: ไม่แย่กว่า FinBERT และ ~75%+
4. ติดตั้ง scheduled job รายวันไหม
5. ซ่อนชิป sentiment ของ Laya จนกว่าจะประเมินไหม
6. อีเมลสำหรับ SEC User-Agent (เมื่อเอา SEC กลับมา)

## ลำดับต่อไป
T0 (ผู้ใช้ติดป้าย) ∥ T2, T3, T9, T10, แก้ `ReasonText` → T1 → rerun T5 บนข่าวที่กรองแล้ว + T6 → T4/T7 เมื่อผู้ใช้เรียก → T8 · ตาราง task: [progress](progress.md)
