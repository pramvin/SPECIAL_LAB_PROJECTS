---
type: Project Brief
title: PlanWise AI brief
description: What the project is, locked decisions, hard rules. Source of truth.
tags: [core]
timestamp: 2026-10-18T20:00:00Z
---

**PlanWise AI** โปรเจกต์จบ: เว็บแนะนำ **หุ้นระยะสั้น S&P 500 แบบเฉพาะบุคคล** พร้อมเหตุผลและข่าว ทำระยะสั้นก่อน ระยะยาวทีหลัง

## ล็อกแล้ว (ห้ามเปิดถกใหม่)
- S&P 500 เท่านั้น · **long only** · ระยะถือ `1w` `1m` `3m`
- **AI ไม่รันบนเครื่องผู้ใช้** → Kaggle + Cloudflare tunnel ([runbook](runbooks/kaggle-gateways.md))
- LLM = Ollama `qwen3:8b` บน Kaggle
- **ไม่ใช้ข้อมูล X/influencer**
- SEC EDGAR + earnings trigger: เลื่อน ผู้ใช้จะเอากลับมาเอง **ห้ามเริ่มเอง**
- ผู้ใช้เขียนไทย → ตอบไทยคำง่ายและสั้น · UI เว็บเป็นอังกฤษ

## กฎห้ามละเมิด
- ห้ามแต่งตัวเลข/สูตร/แหล่งข้อมูล/เหตุผล: ต้องจริงหรือติดป้ายตัวอย่าง
- *Proposal/TBD* = ยังไม่อนุมัติ
- ไม่มีชำระเงิน เทรดจริง หรือเชื่อมธนาคาร · ไม่ใส่ secret ใน frontend
- แสดงแบนเนอร์ "ไม่ใช่คำแนะนำลงทุน / ยังไม่ backtest" · ไม่รับประกันผลตอบแทน
- ถามก่อน: ดาวน์โหลด, อัปโหลด, ติดตั้ง, ตั้ง scheduled job, commit
