---
type: Index
title: PlanWise memory bank
description: Entry point. Read this first, open only the files the task needs.
timestamp: 2026-10-18T20:00:00Z
---

อ่านเฉพาะไฟล์ที่ต้องใช้ ไฟล์ละ 1 เรื่อง แต่ละไฟล์มี `description` ใน frontmatter ให้สแกนก่อนเปิดเนื้อหา

| ไฟล์ | เปิดเมื่อ |
|---|---|
| [projectbrief](projectbrief.md) | ต้องรู้ขอบเขตและกฎที่ล็อกแล้ว (**เปิดทุกครั้ง**) |
| [activeContext](activeContext.md) | จะเริ่มทำงานต่อ: ปัญหาค้าง, รอผู้ใช้ตัดสินใจ (**เปิดทุกครั้ง**) |
| [progress](progress.md) | ดูว่า stage/task ไหนเสร็จแล้ว |
| [productContext](productContext.md) | ต้องเข้าใจเหตุผลเชิงผลิตภัณฑ์ |
| [systemPatterns](systemPatterns.md) | จะแก้โครงสร้าง pipeline / การให้คะแนน |
| [techContext](techContext.md) | stack, ข้อควรระวังด้านเครื่องมือ |
| [runbooks/](runbooks/index.md) | ต้องรันคำสั่ง (refresh ข้อมูล, เปิด Kaggle) |
| [experiments/](experiments/results.md) | ต้องอ้างผลทดลอง Laya / FinBERT / LLM |
| [log](log.md) | ดูประวัติการเปลี่ยนแปลง |

เอกสารต้นทางฉบับเต็ม (อย่าโหลดทั้งฉบับถ้าไม่จำเป็น): `../PIPELINE_SPEC.md`, `../OVERVIEW.md`, `../Backend/README.md`

กฎการดูแล: 1 ไฟล์ = 1 เรื่อง, ลิงก์แทนการคัดลอก, แก้ `timestamp` และเติม [log](log.md) ทุกครั้งที่แก้
