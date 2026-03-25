import jwt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# 🌟 เพิ่ม ForeignKey และ relationship จาก sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from datetime import date
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from fastapi.security import OAuth2PasswordBearer

# ฟังก์ชันสำหรับเปิดและปิดการเชื่อมต่อฐานข้อมูลอัตโนมัติ
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ตั้งค่าฐานข้อมูล PostgreSQL (ใช้ URL ของ Neon ที่คุณครูทำไว้)
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_yA7FNdYx9gPz@ep-blue-wave-a19zu27r-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# บอกโปรแกรมให้ใช้รูปแบบ bcrypt ในการเข้ารหัส
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# สร้างฟังก์ชันสำหรับสับรหัสผ่าน
def get_password_hash(password):
    return pwd_context.hash(password)

# ฟังก์ชันสำหรับเช็ครหัสผ่าน (เทียบรหัสที่พิมพ์มา กับรหัสที่สับแล้วในฐานข้อมูล)
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- ตั้งค่า JWT Token ---
# รหัสลับสำหรับเซ็นรับรอง Token (ห้ามบอกใคร! คุณครูเปลี่ยนข้อความตรงนี้เป็นอะไรก็ได้ยาวๆ ครับ)
SECRET_KEY = "my_super_secret_key_for_smart_wallet" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # บัตรผ่านทางมีอายุ 30 นาที

# ฟังก์ชันสร้าง Token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# บอกยามว่า ประตูทางเข้าสำหรับไปเอาบัตรผ่านทางคือช่องทาง /login นะ
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ฟังก์ชันยามตรวจบัตร (จะสกัดเอา Token มาแกะดูว่าใครคือเจ้าของบัตร)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="ไม่สามารถยืนยันตัวตนได้ (Token อาจจะหมดอายุหรือผิดพลาด)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # ถอดรหัส Token ด้วยกุญแจลับของเรา
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub") # ดึงชื่อผู้ใช้ออกมา
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        # ถ้า Token ปลอม หรือหมดอายุ จะโดนเตะออกตรงนี้ครับ
        raise credentials_exception
        
    # เอาชื่อไปค้นหาในฐานข้อมูลว่ามีตัวตนจริงๆ ไหม
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise credentials_exception
        
    return user # ปล่อยผ่าน! ส่งข้อมูลผู้ใช้คนนั้นเข้าไปในระบบ

# ==========================================
# 🌟 1. สร้างตารางเก็บข้อมูลผู้ใช้ (Users)
# ==========================================
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) # ชื่อผู้ใช้ห้ามซ้ำกัน
    hashed_password = Column(String) # เราจะไม่เก็บรหัสผ่านตรงๆ แต่จะเก็บแบบเข้ารหัส

    # เชื่อมความสัมพันธ์: 1 คน (User) มีได้หลายรายการ (Transactions)
    transactions = relationship("TransactionDB", back_populates="owner")

# ==========================================
# 🌟 2. อัปเดตตารางรายการ (Transactions)
# ==========================================
class TransactionDB(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)               
    title = Column(String, index=True)  
    amount = Column(Float)              
    ttype = Column(String)              
    
    # เพิ่มคอลัมน์ owner_id เพื่อโยงไปหาตาราง users
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # เชื่อมความสัมพันธ์กลับไปหาตาราง User
    owner = relationship("UserDB", back_populates="transactions")

# คำสั่งสร้างตาราง (ถ้ายังไม่มี)
Base.metadata.create_all(bind=engine)

# ... (โค้ดส่วน FastAPI app และ API routes เดิมยังคงไว้ด้านล่าง) ...

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

class UserCreate(BaseModel):
    username: str
    # 🌟 เพิ่ม Field เพื่อจำกัดความยาวรหัสผ่านไม่เกิน 72 ตัวอักษร
    password: str = Field(..., max_length=72, description="รหัสผ่านต้องยาวไม่เกิน 72 ตัวอักษร")

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True  # ใช้ orm_mode = True ถ้าคุณใช้ Pydantic v1

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

@app.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 1. เช็คก่อนว่ามีใครใช้ชื่อ (Username) นี้ไปหรือยัง?
    existing_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้นี้ถูกใช้งานแล้วครับ")
        
    # 2. ถ้ายืนยันว่าชื่อว่าง ก็เอารหัสผ่านไปเข้ารหัส
    hashed_pwd = get_password_hash(user.password)
    
    # 3. สร้าง User ใหม่ และบันทึกลงฐานข้อมูล
    new_user = UserDB(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    # 1. ค้นหาชื่อผู้ใช้ในฐานข้อมูล
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    
    # 2. ถ้าหาชื่อไม่เจอ หรือ รหัสผ่านไม่ตรงกัน
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    
    # 3. ถ้ารหัสผ่านถูกต้อง ให้สร้าง Token โดยประทับตราชื่อ Username ลงไป
    access_token = create_access_token(data={"sub": db_user.username})
    
    # 4. ส่ง Token กลับไปให้ผู้ใช้
    return {"access_token": access_token, "token_type": "bearer"}