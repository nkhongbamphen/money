from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import date

# 1. ตั้งค่าฐานข้อมูล SQLite
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_yA7FNdYx9gPz@ep-blue-wave-a19zu27r-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TransactionDB(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)               # 🌟 เพิ่มคอลัมน์ วันที่
    title = Column(String, index=True)  
    amount = Column(Float)              
    ttype = Column(String)              

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 🌟 เพิ่ม date ใน Pydantic Model
class TransactionCreate(BaseModel):
    date: str
    title: str
    amount: float
    ttype: str

# ==========================================
# 2. API สำหรับจัดการบัญชี
# ==========================================

@app.get("/transactions")
def get_transactions(db: Session = Depends(get_db)):
    # ดึงข้อมูลเรียงตามวันที่ล่าสุด และ ID ล่าสุด
    transactions = db.query(TransactionDB).order_by(TransactionDB.date.desc(), TransactionDB.id.desc()).all()
    return {"transactions": transactions}

@app.post("/transactions")
def add_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    # 🌟 บันทึกวันที่ลงไปในฐานข้อมูลด้วย
    new_tx = TransactionDB(date=tx.date, title=tx.title, amount=tx.amount, ttype=tx.ttype)
    db.add(new_tx)
    db.commit()
    return {"message": "บันทึกรายการสำเร็จ!"}

@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(TransactionDB).filter(TransactionDB.id == tx_id).first()
    if tx:
        db.delete(tx)
        db.commit()
    return {"message": "ลบสำเร็จ"}