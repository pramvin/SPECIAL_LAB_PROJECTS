---
type: Experiment Results
title: Laya / FinBERT / LLM experiments
description: Numbers from Kaggle T4 runs 2026-10-16/17. Single runs, no CI, no gold labels on own headlines.
tags: [evaluation]
timestamp: 2026-10-18T20:00:00Z
---

**A: ชุดสาธารณะ** (`zeroshot/twitter-financial-news-sentiment`, 2,388)
| โมเดล | Acc | Macro F1 |
|---|---|---|
| FinBERT | 0.725 | 0.668 |
| Laya English | 0.796 | 0.736 |
| Laya typed-decisions | 0.767 | 0.731 |

ความเร็วเทียบไม่ได้ (batch vs loop) · Laya เอนไป neutral, FinBERT ผิดทางตรงข้าม

**B: headline ของเรา** (1,000 จาก 12,801): FinBERT↔Laya **เห็นตรงกัน** 74.1% = ความสอดคล้อง **ไม่ใช่ความแม่น** · `kind`: Laya เรียก filler 138 จาก 924 ที่กฎไม่ติดธง; เห็นด้วยกับกฎ 17 จาก 76 ที่ติดธง (ยังไม่รู้ใครถูก)

**C: LLM `qwen3:8b`, temp 0, 42 ticker:** JSON ถูกทั้งหมด · 8.8 วิ/ตัว · up 36/down 2/none 6 · confidence สูง (0.7-0.75) · ยังไม่ตรวจความแม่น

**เกณฑ์ที่เสนอ (ผู้ใช้ยังไม่อนุมัติ):** บนป้าย 200 แถว Laya ไม่แย่กว่า FinBERT และ ~75%+ ไม่งั้น fine-tune (`github.com/NandhaKishorM/laya`, `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`) · Laya probabilities **ไม่ calibrated**
