---
type: Active Context
title: Current focus
description: Open problems, pending user decisions, next order of work. Update most often.
tags: [active]
timestamp: 2026-10-30T18:14:51Z
---

**โฟกัส:** Stage 5 (LLM) รันครั้งแรกแล้ว 42/42 → ต้องทำให้เชื่อถือได้: แก้บั๊ก UI, กวาดไฟล์ซ้ำ, ให้ผู้ใช้ติดป้ายเพื่อวัดความแม่น

**UI decision (2026-10-31):** Trade Ideas ticker opens its TradingView chart in a new tab; intervals are 1w → 4H, 1m → 1D, and 3m → 1D. Use a direct chart link, with no widget or API key.

## ปัญหาค้าง
1. `ReasonText` (`IdeasView.tsx`) ใส่ `[1]` ทุกลิงก์; id ที่ไม่อยู่ใน `cited_news_ids` เป็นเลขเปล่า
2. ป้าย Laya ดูผิดในเคสชัด (MA ข่าวดีได้ Bearish) · ยังไม่มี ground truth
3. LLM เอนเอียง bullish (up 36/down 2/none 6)
4. Laya กับ LLM ยังไม่ต่อกัน (LLM อ่านทุก headline ที่ `rule_noise=0`)
5. ~~ไฟล์ LLM-server ซ้ำ~~ ลบแล้ว 10-27 เหลือ `kaggle_gateways.ipynb` ทางเดียว
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

## ทดลองที่เขียนโค้ดแล้ว (anon รันแล้ว; Kaggle อาจยังเปิดอยู่ ให้หยุด session)
`python -m pipeline.llm_ab --arm anon` (ปิดชื่อบริษัท) และ `--arm think` (ล้มเหลว ดู results ข้อ F; ตัดสินใจคงโหมดคิดปิด) · ผลเทียบกับ A เท่านั้น ยังไม่มีป้ายคนติด · `python -m pipeline.disagree` ธง 13/42 หุ้นที่ LLM กับ Laya เห็นต่าง

## ชั้นตัวเลขยืนยัน (คุยเมื่อ 10-26 ยังไม่ล็อก ผู้ใช้ยังไม่อนุมัติแผน)
ปัญหา: Laya (= "JEV" ที่ผู้ใช้เรียก) กับ LLM ออกเป็นข้อความ ไม่รู้ถูกหรือมั่ว → ต้องมีตัวเลขที่อธิบายว่าทำไมขึ้น/ลง
- แนวที่เสนอ: เทียบป้าย Laya/LLM กับ **ผลราคาจริงหลังข่าว** (1w/1m/3m เทียบตลาด) แล้วแสดง "ข่าวแบบนี้เคยเกิด N ครั้ง ชนะตลาด Y%" + ช่วงไม่แน่นอน · ทางเสริม: ประเมินความผันผวน (ทำนายได้ดีกว่าทิศทาง)
- ไม่ทำโมเดลอ่านข้อความตัวที่ 3 · deep learning รอข้อมูลมากพอ (ตอนนี้ ~200 ข่าว น้อยเกิน) · อาจได้ผล "สัญญาณอ่อน" ซึ่งต้องบอกผู้ใช้ตรงๆ
- ต้องถามก่อนดึงข่าวย้อนหลังจาก FMP (ดาวน์โหลด) · ถ้าใช้ 5/10/15 วันแทน 1w/1m/3m ต้องให้ผู้ใช้อนุมัติ (กรอบที่ล็อกคือ 1w/1m/3m)
- อาจารย์ที่ปรึกษา (Wen Huang, USTC, คณิตศาสตร์บริสุทธิ์): งานไม่ตรงหัวข้อ ห้ามอ้างว่าเป็นฐานของโปรเจกต์

## FMP (ทดสอบ 10-27)
key ใน `Backend/.env` (`FMP_API_KEY`) ใช้ได้กับ `quote`, `profile`, `search-symbol`, ราคา EOD · **402** กับ `sp500-constituent`, `etf/holdings`, `stock-list`, screener → รายชื่อ S&P 500 ใช้ Wikipedia ต่อ · ยังไม่ได้ทดสอบข่าว FMP · ผู้ใช้ควรสร้าง key ใหม่ (key เคยอยู่ในแชท)

## แบ่งงานทีม (ส่งเพื่อนแล้ว 10-27)
Han = login/security · Vincent = แบบสอบถาม + บันทึกคำตอบลง DB · Steven = กราฟ · Adrian = ค้นหา + watchlist ลง DB · แจ้งว่ารายชื่อ S&P 500 อยู่ใน DB แล้ว (Wikipedia, ราคา yfinance) · 60–80% win rate เป็นเป้าที่ต้อง backtest ไม่ใช่คำรับประกัน

## ลำดับต่อไป
T0 (ผู้ใช้ติดป้าย) ∥ T2, T3, T9, T10, แก้ `ReasonText` → T1 → rerun T5 บนข่าวที่กรองแล้ว + T6 → T4/T7 เมื่อผู้ใช้เรียก → T8 · ตาราง task: [progress](progress.md)
