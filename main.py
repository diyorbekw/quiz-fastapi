from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import aiosqlite
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import httpx
import html as html_escape
from datetime import datetime, timedelta
import re
import json

load_dotenv()

app = FastAPI(title="Quiz API", version="1.0", description="API for managing quiz questions and categories")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "quiz.db"
BOT_TOKEN = "8419378575:AAEjSLGNp3NbbokZctmediBYPLFFDrtvos8"
ADMIN_CHAT_ID = -1002717944928
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
THREAD_ID = 3

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = "📚"
    time: Optional[int] = 10

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class QuestionBase(BaseModel):
    question: str
    a_var: str
    b_var: str
    c_var: str
    d_var: str
    answer: str
    category_id: int

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int

    class Config:
        from_attributes = True

class ResultPayload(BaseModel):
    telegram_id: Optional[int] = None
    full_name: Optional[str] = None
    username: Optional[str] = None
    category: str
    questions_count: int
    correct_answers_count: int
    correct_answers_percent: int
    spent_time: str
    school: Optional[str] = None
    grade: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None

class LeaderboardEntry(BaseModel):
    full_name: str
    correct_answers: int
    total_questions: int
    percentage: int
    category: str
    spent_time: str
    date: str
    school: Optional[str] = None
    grade: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None

class LeaderboardResponse(BaseModel):
    data: List[LeaderboardEntry]
    categories: List[Category]

class SchoolLeaderboardEntry(BaseModel):
    school: str
    total_correct_answers: int
    total_questions: int
    average_percentage: float
    total_participants: int
    region: str
    district: str

class GradeLeaderboardEntry(BaseModel):
    grade: int
    total_correct_answers: int
    total_questions: int
    average_percentage: float
    total_participants: int

# SQLite connection
db_connection = None

@app.on_event("startup")
async def startup():
    global db_connection
    db_connection = await aiosqlite.connect(DATABASE_URL)
    await create_tables()

@app.on_event("shutdown")
async def shutdown():
    await db_connection.close()

async def create_tables():
    async with db_connection.cursor() as cursor:
        # Users table for school and grade information
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                region TEXT,
                district TEXT,
                school TEXT,
                grade INTEGER
            )
        """)
        
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT DEFAULT '📚',
                description TEXT,
                time INTEGER NOT NULL DEFAULT 10
            )
        """)
        
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                a_var TEXT NOT NULL,
                b_var TEXT NOT NULL,
                c_var TEXT NOT NULL,
                d_var TEXT NOT NULL,
                answer TEXT NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D')),
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                full_name TEXT,
                username TEXT,
                category TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                questions_count INTEGER NOT NULL,
                correct_answers_count INTEGER NOT NULL,
                correct_answers_percent INTEGER NOT NULL,
                spent_time TEXT NOT NULL,
                school TEXT,
                grade INTEGER,
                region TEXT,
                district TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db_connection.commit()

async def get_db():
    return db_connection

# User management endpoints
@app.get("/users/{telegram_id}")
async def get_user(telegram_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT * FROM users WHERE user_id = ?", (telegram_id,))
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": record[0],
            "user_id": record[1],
            "first_name": record[2],
            "last_name": record[3],
            "phone_number": record[4],
            "region": record[5],
            "district": record[6],
            "school": record[7],
            "grade": record[8]
        }

@app.post("/users/")
async def create_user(user_data: dict, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, first_name, last_name, phone_number, region, district, school, grade) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_data['user_id'],
            user_data['first_name'],
            user_data['last_name'],
            user_data['phone_number'],
            user_data['region'],
            user_data['district'],
            user_data['school'],
            user_data['grade']
        ))
        await db.commit()
        return {"status": "success"}

# Categories endpoints (unchanged)
@app.post("/categories/", response_model=Category, status_code=201)
async def add_category(category: CategoryCreate, db=Depends(get_db)):
    query = """
        INSERT INTO categories (name, description, emoji, time)
        VALUES (?, ?, ?, ?)
    """
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                query,
                (category.name, category.description, category.emoji, category.time)
            )
            await db.commit()
            
            await cursor.execute("SELECT * FROM categories WHERE id = last_insert_rowid()")
            record = await cursor.fetchone()
            
            if record:
                return Category(
                    id=record[0],
                    name=record[1],
                    emoji=record[2],
                    description=record[3],
                    time=record[4]
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to create category")
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Category name already exists.")

@app.get("/categories/", response_model=List[Category])
async def get_categories(limit: int = 10, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT id, name, emoji, description, time FROM categories LIMIT ?", (limit,))
        records = await cursor.fetchall()
        return [
            Category(
                id=record[0],
                name=record[1],
                emoji=record[2],
                description=record[3],
                time=record[4]
            ) for record in records
        ]

@app.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT id, name, emoji, description, time FROM categories WHERE id = ?", (category_id,))
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Category not found.")
        return Category(
            id=record[0],
            name=record[1],
            emoji=record[2],
            description=record[3],
            time=record[4]
        )

@app.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found.")

# Questions endpoints (unchanged)
@app.post("/questions/", response_model=Question, status_code=201)
async def add_question(question: QuestionCreate, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT 1 FROM categories WHERE id = ?", (question.category_id,))
        category_exists = await cursor.fetchone()
        if not category_exists:
            raise HTTPException(status_code=400, detail="Category does not exist.")
    
    query = """
        INSERT INTO questions (question, a_var, b_var, c_var, d_var, answer, category_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    question.question,
                    question.a_var,
                    question.b_var,
                    question.c_var,
                    question.d_var,
                    question.answer.upper(),
                    question.category_id
                )
            )
            await db.commit()
            
            await cursor.execute("SELECT * FROM questions WHERE id = last_insert_rowid()")
            record = await cursor.fetchone()
            
            if record:
                return Question(
                    id=record[0],
                    question=record[1],
                    a_var=record[2],
                    b_var=record[3],
                    c_var=record[4],
                    d_var=record[5],
                    answer=record[6],
                    category_id=record[7]
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to create question")
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.put("/questions/{question_id}", response_model=Question)
async def update_question(question_id: int, question: QuestionCreate, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT 1 FROM categories WHERE id = ?", (question.category_id,))
        category_exists = await cursor.fetchone()
        if not category_exists:
            raise HTTPException(status_code=400, detail="Category does not exist.")
    
    query = """
        UPDATE questions
        SET question = ?, a_var = ?, b_var = ?, c_var = ?, d_var = ?, answer = ?, category_id = ?
        WHERE id = ?
    """
    try:
        async with db.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    question.question,
                    question.a_var,
                    question.b_var,
                    question.c_var,
                    question.d_var,
                    question.answer.upper(),
                    question.category_id,
                    question_id
                )
            )
            await db.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Question not found.")
            
            await cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
            record = await cursor.fetchone()
            
            if record:
                return Question(
                    id=record[0],
                    question=record[1],
                    a_var=record[2],
                    b_var=record[3],
                    c_var=record[4],
                    d_var=record[5],
                    answer=record[6],
                    category_id=record[7]
                )
            else:
                raise HTTPException(status_code=404, detail="Question not found.")
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found.")

@app.get("/questions/{question_id}", response_model=Question)
async def get_question(question_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE id = ?",
            (question_id,)
        )
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Question not found.")
        return Question(
            id=record[0],
            question=record[1],
            a_var=record[2],
            b_var=record[3],
            c_var=record[4],
            d_var=record[5],
            answer=record[6],
            category_id=record[7]
        )

@app.get("/categories/{category_id}/questions", response_model=List[Question])
async def get_questions_by_category(category_id: int, db=Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,))
        category_exists = await cursor.fetchone()
        if not category_exists:
            raise HTTPException(status_code=404, detail="Category not found.")
        
        await cursor.execute(
            "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE category_id = ?",
            (category_id,)
        )
        records = await cursor.fetchall()
        return [
            Question(
                id=record[0],
                question=record[1],
                a_var=record[2],
                b_var=record[3],
                c_var=record[4],
                d_var=record[5],
                answer=record[6],
                category_id=record[7]
            ) for record in records
        ]

# Results endpoints (updated with school/grade info)
@app.post("/results", status_code=202)
async def save_result(payload: ResultPayload, db=Depends(get_db)):
    # Get user data if available
    user_data = None
    if payload.telegram_id:
        async with db.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE user_id = ?", (payload.telegram_id,))
            user_data = await cursor.fetchone()

    # Get category ID
    async with db.cursor() as cursor:
        await cursor.execute("SELECT id FROM categories WHERE name = ?", (payload.category,))
        category_record = await cursor.fetchone()
        category_id = category_record[0] if category_record else None

        # Save to database with school/grade info
        query = """
            INSERT INTO results (
                telegram_id, full_name, username, category, category_id,
                questions_count, correct_answers_count, correct_answers_percent, spent_time,
                school, grade, region, district
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await cursor.execute(
            query,
            (
                payload.telegram_id,
                payload.full_name,
                payload.username,
                payload.category,
                category_id,
                payload.questions_count,
                payload.correct_answers_count,
                payload.correct_answers_percent,
                payload.spent_time,
                payload.school or (user_data[7] if user_data else None),
                payload.grade or (user_data[8] if user_data else None),
                payload.region or (user_data[5] if user_data else None),
                payload.district or (user_data[6] if user_data else None)
            )
        )
        await db.commit()

    # Send to admin
    if payload.telegram_id and payload.full_name:
        safe_name = html_escape.escape(payload.full_name)
        mention_html = f'<a href="tg://user?id={payload.telegram_id}">{safe_name}</a>'
    elif payload.full_name:
        mention_html = html_escape.escape(payload.full_name)
    else:
        mention_html = "Noma'lum foydalanuvchi"

    school_info = ""
    if payload.school:
        school_info = f"🏫 Maktab: {html_escape.escape(payload.school)}\n"
    if payload.grade:
        school_info += f"🎓 Sinf: {payload.grade}\n"

    message = f"""
Yangi test natijasi:
👤 Foydalanuvchi: {mention_html}
{school_info}
📝 Mavzu: {html_escape.escape(payload.category)}
❓ Savollar soni: {payload.questions_count}
✅ To'g'ri javoblar: {payload.correct_answers_count}
🎯 Foiz: {payload.correct_answers_percent}%
⏳ Vaqt: {payload.spent_time}
    """

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TG_API}/sendMessage",
            json = {
                "chat_id": ADMIN_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "message_thread_id": THREAD_ID 
            }
        )

    return {"status": "ok"}

# Leaderboard endpoints
@app.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    time_filter: str = "24h",
    category_id: Optional[int] = None,
    db=Depends(get_db)
):
    now = datetime.now()
    if time_filter == "24h":
        time_condition = f"timestamp >= '{now - timedelta(hours=24)}'"
    elif time_filter == "week":
        time_condition = f"timestamp >= '{now - timedelta(days=7)}'"
    elif time_filter == "month":
        time_condition = f"timestamp >= '{now.replace(day=1)}'"
    else:
        time_condition = "1=1"
    
    category_condition = "1=1" if category_id is None else f"category_id = {category_id}"
    
    leaderboard_query = f"""
    SELECT 
        full_name,
        correct_answers_count as correct_answers,
        questions_count as total_questions,
        correct_answers_percent as percentage,
        category,
        spent_time,
        strftime('%Y-%m-%d %H:%M', timestamp) as date,
        school,
        grade,
        region,
        district
    FROM results
    WHERE {time_condition} AND {category_condition}
    ORDER BY percentage DESC, correct_answers DESC
    LIMIT 10
    """
    
    async with db.cursor() as cursor:
        await cursor.execute(leaderboard_query)
        records = await cursor.fetchall()
        leaderboard_data = [
            LeaderboardEntry(
                full_name=record[0],
                correct_answers=record[1],
                total_questions=record[2],
                percentage=record[3],
                category=record[4],
                spent_time=record[5],
                date=record[6],
                school=record[7],
                grade=record[8],
                region=record[9],
                district=record[10]
            ) for record in records
        ]
        
        await cursor.execute("SELECT id, name, emoji, description, time FROM categories ORDER BY name")
        category_records = await cursor.fetchall()
        categories_list = [
            Category(
                id=record[0],
                name=record[1],
                emoji=record[2],
                description=record[3],
                time=record[4]
            ) for record in category_records
        ]
    
    return LeaderboardResponse(
        data=leaderboard_data,
        categories=categories_list
    )

@app.get("/leaderboard/schools")
async def get_school_leaderboard(
    time_filter: str = "all",
    region: Optional[str] = None,
    district: Optional[str] = None,
    db=Depends(get_db)
):
    now = datetime.now()
    if time_filter == "24h":
        time_condition = f"timestamp >= '{now - timedelta(hours=24)}'"
    elif time_filter == "week":
        time_condition = f"timestamp >= '{now - timedelta(days=7)}'"
    elif time_filter == "month":
        time_condition = f"timestamp >= '{now.replace(day=1)}'"
    else:
        time_condition = "1=1"
    
    region_condition = "1=1" if not region else f"region = '{region}'"
    district_condition = "1=1" if not district else f"district = '{district}'"
    
    query = f"""
    SELECT 
        school,
        region,
        district,
        SUM(correct_answers_count) as total_correct_answers,
        SUM(questions_count) as total_questions,
        AVG(correct_answers_percent) as average_percentage,
        COUNT(DISTINCT telegram_id) as total_participants
    FROM results
    WHERE school IS NOT NULL AND {time_condition} AND {region_condition} AND {district_condition}
    GROUP BY school, region, district
    ORDER BY average_percentage DESC, total_correct_answers DESC
    LIMIT 20
    """
    
    async with db.cursor() as cursor:
        await cursor.execute(query)
        records = await cursor.fetchall()
        
        return [
            SchoolLeaderboardEntry(
                school=record[0],
                region=record[1],
                district=record[2],
                total_correct_answers=record[3],
                total_questions=record[4],
                average_percentage=round(record[5], 2),
                total_participants=record[6]
            ) for record in records
        ]

@app.get("/leaderboard/grades")
async def get_grade_leaderboard(
    time_filter: str = "all",
    grade: Optional[int] = None,
    db=Depends(get_db)
):
    now = datetime.now()
    if time_filter == "24h":
        time_condition = f"timestamp >= '{now - timedelta(hours=24)}'"
    elif time_filter == "week":
        time_condition = f"timestamp >= '{now - timedelta(days=7)}'"
    elif time_filter == "month":
        time_condition = f"timestamp >= '{now.replace(day=1)}'"
    else:
        time_condition = "1=1"
    
    grade_condition = "1=1" if grade is None else f"grade = {grade}"
    
    query = f"""
    SELECT 
        grade,
        SUM(correct_answers_count) as total_correct_answers,
        SUM(questions_count) as total_questions,
        AVG(correct_answers_percent) as average_percentage,
        COUNT(DISTINCT telegram_id) as total_participants
    FROM results
    WHERE grade IS NOT NULL AND {time_condition} AND {grade_condition}
    GROUP BY grade
    ORDER BY average_percentage DESC, total_correct_answers DESC
    """
    
    async with db.cursor() as cursor:
        await cursor.execute(query)
        records = await cursor.fetchall()
        
        return [
            GradeLeaderboardEntry(
                grade=record[0],
                total_correct_answers=record[1],
                total_questions=record[2],
                average_percentage=round(record[3], 2),
                total_participants=record[4]
            ) for record in records
        ]

# User results endpoints
@app.get("/results/{telegram_id}")
async def get_user_results(telegram_id: int, db=Depends(get_db)) -> Dict:
    query = """
        SELECT 
            full_name,
            username,
            category,
            questions_count,
            correct_answers_count,
            correct_answers_percent,
            spent_time,
            strftime('%Y-%m-%d %H:%M', timestamp) as date,
            school,
            grade,
            region,
            district
        FROM results
        WHERE telegram_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """
    async with db.cursor() as cursor:
        await cursor.execute(query, (telegram_id,))
        record = await cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Natijalar topilmadi")
        
        return {
            "full_name": record[0],
            "username": record[1],
            "category": record[2],
            "questions_count": record[3],
            "correct_answers_count": record[4],
            "correct_answers_percent": record[5],
            "spent_time": record[6],
            "date": record[7],
            "school": record[8],
            "grade": record[9],
            "region": record[10],
            "district": record[11]
        }

@app.get("/results/{telegram_id}/all")
async def get_user_all_results(telegram_id: int, db=Depends(get_db)) -> List[Dict]:
    query = """
        SELECT 
            full_name,
            username,
            category,
            questions_count,
            correct_answers_count,
            correct_answers_percent,
            spent_time,
            strftime('%Y-%m-%d %H:%M', timestamp) as date,
            school,
            grade,
            region,
            district
        FROM results
        WHERE telegram_id = ?
        ORDER BY timestamp DESC
    """
    async with db.cursor() as cursor:
        await cursor.execute(query, (telegram_id,))
        records = await cursor.fetchall()
        if not records:
            raise HTTPException(status_code=404, detail="Natijalar topilmadi")
        
        return [
            {
                "full_name": record[0],
                "username": record[1],
                "category": record[2],
                "questions_count": record[3],
                "correct_answers_count": record[4],
                "correct_answers_percent": record[5],
                "spent_time": record[6],
                "date": record[7],
                "school": record[8],
                "grade": record[9],
                "region": record[10],
                "district": record[11]
            } for record in records
        ]

# AI Test generation endpoint
@app.get("/ai-test")
async def generate_ai_test_questions(
    topic: str,
    count: int
):
    if count < 1 or count > 25:
        raise HTTPException(
            status_code=400,
            detail="Count must be between 1 and 25 inclusive"
        )

    openai_api_key = "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"
    if not openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured"
        )

    prompt = f"""
    Siz {topic} mavzusida {count} ta test savolini O'zbek tilida (Lotin alifbosida) yaratishingiz kerak.
    
    HAR BIR SAVOL QUYIDAGI FORMATDA BO'LISHI SHART:
    - "question": savol matni
    - "a_var": A variant javobi
    - "b_var": B variant javobi  
    - "c_var": C variant javobi
    - "d_var": D variant javobi
    - "answer": To'g'ri javob (A, B, C yoki D)

    MUHIM TA'KIDLAR:
    1. Faqat JSON formatida qaytaring, boshqa izoh yoki matn qo'shmang
    2. Barcha matnlar O'zbek tilida (Lotin alifbosida) bo'lsin
    3. "answer" faqat A, B, C yoki D harflaridan biri bo'lsin
    4. JSON array ichida {count} ta savol bo'lsin
    5. Har bir savol objecti yuqoridagi formatga mos kelishi shart

    MISOL FORMAT:
    [
      {{
        "question": "Savol matni shu yerda",
        "a_var": "A variant",
        "b_var": "B variant", 
        "c_var": "C variant",
        "d_var": "D variant",
        "answer": "A"
      }}
    ]

    Endi {topic} mavzusida {count} ta savol yarating:
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Siz test savollarini yaratuvchi yordamchisiz. Faqat JSON formatida javob qaytaring. Hech qanday qo'shimcha matn yozmang."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI API error: {response.text}"
                )

            data = response.json()
            ai_response = data["choices"][0]["message"]["content"].strip()

            ai_response = re.sub(r'```json\s*|\s*```', '', ai_response)
            ai_response = ai_response.strip()

            questions = json.loads(ai_response)

            if not isinstance(questions, list):
                raise ValueError("AI response is not a list")

            for question in questions:
                required_fields = ["question", "a_var", "b_var", "c_var", "d_var", "answer"]
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"Missing field: {field}")
                
                if question["answer"] not in ["A", "B", "C", "D"]:
                    raise ValueError(f"Invalid answer: {question['answer']}")

            return questions

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI response is not valid JSON: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI response validation failed: {str(e)}"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API request timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )

# ChatGPT yordamida savolning to'liq yechimi endpoint'i
@app.get("/explain-solution")
async def explain_solution(question: str):
    """
    ChatGPT yordamida savolning to'liq yechim jarayonini tushuntirish
    """
    openai_api_key = "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"
    
    if not openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured"
        )

    if not question or len(question.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Question parameter is required"
        )

    prompt = f"""
    Quyidagi savolga to'liq va batafsil yechim bering. Yechim quyidagi strukturaga ega bo'lsin:

    1. SAVOLNI TUSHUNISH: Savol nimani so'rayotganini tushuntiring
    2. ASOSIY TUSHUNCHALAR: Savol bilan bog'liq muhim tushunchalarni qisqacha izohlang
    3. YECHIM JARAYONI: Qadamma-qadam yechim berish metodikasini ko'rsating
    4. JAVOB: Yakuniy javobni aniq ko'rsating

    Har bir qism qisqa va aniq bo'lsin. Umumiy yechim maksimum 6-8 jumla bo'lsin.
    Hech qanday markdown, smaylik, raqamlash yoki maxsus formatlash ishlatmang.
    Faqat oddiy matn qaytaring. O'zbek tilida (Lotin alifbosida) javob bering.

    Savol: {question}

    To'liq yechim:
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Siz o'qituvchi yordamchisiz. Savollarga to'liq va batafsil yechim berasiz, qadamma-qadam tushuntirasiz. Faqat oddiy matn formatida javob qaytarasiz. Hech qanday raqamlar, belgilar yoki maxsus formatlash ishlatmasdan, tabiiy o'zbek tilida yozasiz."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=20.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI API error: {response.text}"
                )

            data = response.json()
            ai_response = data["choices"][0]["message"]["content"].strip()

            # Qo'shimcha tozalash
            ai_response = re.sub(r'[*_`#\-]', '', ai_response)  # Markdown va boshqa belgilarini olib tashlash
            ai_response = re.sub(r'\n+', '\n', ai_response)     # Ortiqcha yangi qatorlarni olib tashlash
            ai_response = re.sub(r'\s+', ' ', ai_response)      # Ortiqcha bo'shliqlarni olib tashlash
            ai_response = ai_response.strip()

            return {"solution": ai_response}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API request timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate solution: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1234)