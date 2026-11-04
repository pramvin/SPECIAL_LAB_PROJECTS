# PlanWise AI

ความรู้ของโปรเจกต์อยู่ในชุด **OKF** (Open Knowledge Format) ที่ `.okf/` แทน `memory-bank/` เดิม
เครื่องมือ: skill `okf` และ `validate` อยู่ใน `.claude/skills/` (Claude Code โหลดให้เองเมื่อเปิดโปรเจกต์นี้)
ส่วน frontend ดูกฎเพิ่มที่ `frontend/AGENTS.md`

## กฎ: อ่าน `.okf/` ก่อนลงมือทุกครั้ง (mode consume)

ก่อนเริ่มงานใดๆ ในรีโปนี้ (แก้โค้ด รันคำสั่ง ตอบคำถามเรื่องโปรเจกต์ วางแผน):

1. เปิด `.okf/index.md` แล้วอ่าน `/project/brief.md` และ `/project/active-context.md` เสมอ
2. เปิดเฉพาะ concept ที่เกี่ยวกับงาน ดูจากรายการและ `description` ใน `index.md` เช่น
   - แก้ pipeline/คะแนน → `/architecture/system-patterns.md`, `/architecture/scoring.md`
   - login/ความปลอดภัย → `/architecture/auth-security.md`
   - รันข้อมูล/เปิด Kaggle → `/runbooks/`
   - อ้างผลโมเดล → `/experiments/results.md`
   - ดูว่าอะไรเสร็จแล้ว/ใครทำอะไร → `/project/progress.md`, `/project/team.md`
3. อย่าโหลดทั้ง `.okf/` และอย่าโหลด `PIPELINE_SPEC.md` ทั้งฉบับ ถ้า concept ตอบได้แล้ว
4. concept ที่ `status: draft`/`deprecated` หรือไม่มี `verified` = ตรวจกับโค้ดก่อนเชื่อ
5. `.okf/` ขัดกับโค้ดหรือสถานะจริง → เชื่อของจริง แล้วแก้ `.okf/`

## กฎ: อัปเดต `.okf/` หลังทำงาน (mode maintain)

เมื่อจบงานที่เปลี่ยนสถานะ การตัดสินใจ หรือปัญหาค้าง ให้ใช้ skill `okf` (maintain):

- แก้ concept ที่ได้รับผลกระทบ **ทุกไฟล์ในรอบเดียว** (ส่วนใหญ่ `/project/active-context.md` และ `/project/progress.md`) และอัปเดต `generated: { by, at }`
  - `by` ตาม actor convention: เอเจนต์ = `<ชื่อ>/<รุ่น>` เช่น `claude-code/claude-sonnet-5-5` · คน = `human:<id>` · งานอัตโนมัติ = `process:<id>`
  - ใช้ `human:` เมื่อคนเขียนหรือยืนยันเอง
- **ทุกครั้งที่ทำงานเสร็จ ให้เพิ่มข้อมูลอัปเดตใหม่ และลบข้อมูลเก่าที่ถูกแทนที่ในรอบเดียวกัน:** เขียนสถานะใหม่ทับของเดิม ห้ามต่อท้ายจนมีทั้งเก่าและใหม่ซ้อนกันหรือขัดกัน (ยกเว้น `log.md` ที่ห้ามลบ)
- **เก็บเฉพาะสถานะปัจจุบัน:** ปัญหาที่แก้แล้ว/งานที่เสร็จแล้วให้ลบออกจาก concept (ประวัติอยู่ใน git) อย่าขีดฆ่าค้างไว้
- concept ที่เลิกใช้ → `status: deprecated` แล้วบันทึกใน `log.md` หรือลบถ้าไม่มีค่าแล้ว
- `log.md` เฉพาะเหตุการณ์วงจรชีวิต (สร้าง bundle, เลิกใช้, แทนที่, สร้างใหม่หลังต้นทางเปลี่ยน, ตรวจยืนยัน) · แก้ปกติไม่ต้องลง · ห้ามลบหรือแก้รายการเก่า · ใหม่สุดอยู่บน
- รักษารูปแบบ: 1 ไฟล์ = 1 เรื่อง, ลิงก์แบบ `/path/file.md`, ไฟล์สั้น (ไม่ควรเกิน ~3 KB)
- ไม่ใส่ secret/token และไม่เก็บสิ่งที่อ่านได้จากโค้ดหรือ git history อยู่แล้ว
- เสร็จแล้วต้อง validate ให้ผ่านก่อนบอกว่าจบ:

```bash
uv run .claude/skills/validate/scripts/okf_validate.py .okf --strict
```

- concept ใหม่: เริ่มจาก `.claude/skills/okf/templates/concept.md` แล้วเพิ่มบรรทัดใน `.okf/index.md`
- ข้อบังคับเดียวของ OKF: ทุก `.md` ที่ไม่ใช่ `index.md`/`log.md` ต้องมี frontmatter และ `type` ไม่ว่าง · `description` ที่มี `: ` ต้องใส่เครื่องหมายคำพูด

## ข้อมูลด่วน

ตอบผู้ใช้เป็นภาษาไทยคำง่ายและสั้น · ถามก่อน commit/ติดตั้ง/ดาวน์โหลด/ตั้ง scheduled job · รายละเอียดกฎทั้งหมดอยู่ใน `.okf/project/brief.md`
