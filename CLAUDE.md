# PlanWise AI

## กฎ: อ่าน memory bank ก่อนลงมือทุกครั้ง

ก่อนเริ่มงานใดๆ ในรีโปนี้ (แก้โค้ด รันคำสั่ง ตอบคำถามเรื่องโปรเจกต์ วางแผน):

1. เปิด `memory-bank/index.md` แล้วอ่านทั้ง `projectbrief.md` และ `activeContext.md` เสมอ
2. เปิดเฉพาะไฟล์อื่นที่เกี่ยวกับงานนั้น ดูจากตารางใน `index.md` และ `description` ใน frontmatter เช่น
   - แก้ pipeline/คะแนน → `systemPatterns.md`
   - รันข้อมูล/เปิด Kaggle → `runbooks/`
   - อ้างผลโมเดล → `experiments/results.md`
   - ดูว่าอะไรเสร็จแล้ว → `progress.md`
3. อย่าโหลดทั้ง memory bank และอย่าโหลด `PIPELINE_SPEC.md` ทั้งฉบับ ถ้าไฟล์ใน memory bank ตอบได้แล้ว
4. memory bank ขัดกับโค้ดหรือสถานะจริง → เชื่อของจริง แล้วแก้ memory bank

## กฎ: อัปเดต memory bank หลังทำงาน

เมื่อจบงานที่เปลี่ยนสถานะ การตัดสินใจ หรือปัญหาค้าง:

- แก้ไฟล์ที่เกี่ยวข้อง (ส่วนใหญ่ `activeContext.md` และ `progress.md`) และอัปเดต `timestamp` ใน frontmatter
- เติมบรรทัดใหม่ไว้บนสุดของ `memory-bank/log.md`
- รักษารูปแบบ: 1 ไฟล์ = 1 เรื่อง, ลิงก์แทนการคัดลอก, ไฟล์สั้น (ไม่ควรเกิน ~3 KB)
- ไม่ใส่ secret/token และไม่เก็บสิ่งที่อ่านได้จากโค้ดหรือ git history อยู่แล้ว

## ข้อมูลด่วน

ตอบผู้ใช้เป็นภาษาไทยคำง่ายและสั้น · ถามก่อน commit/ติดตั้ง/ดาวน์โหลด/ตั้ง scheduled job · รายละเอียดกฎทั้งหมดอยู่ใน `memory-bank/projectbrief.md`
