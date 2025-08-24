from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncpg
from asyncpg.pool import Pool
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import ssl
import httpx
import html as html_escape

load_dotenv()

app = FastAPI(title="Quiz API", version="1.0", description="API for managing quiz questions and categories")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL="postgresql://diyorbekw:iWvq1YE5BRrBWl2sFwVBDvMJon4LSodl@dpg-d2big7adbo4c73asdrcg-a.oregon-postgres.render.com/quizdb_6eiq"
BOT_TOKEN="8419378575:AAEjSLGNp3NbbokZctmediBYPLFFDrtvos8"
ADMIN_CHAT_ID=-1002717944928
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
THREAD_ID=3

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

class LeaderboardEntry(BaseModel):
    full_name: str
    correct_answers: int
    total_questions: int
    percentage: int
    category: str
    spent_time: str
    date: str 

class LeaderboardResponse(BaseModel):
    data: List[LeaderboardEntry]
    categories: List[Category]

pool: Pool = None

@app.on_event("startup")
async def startup():
    global pool
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        ssl=ssl_ctx
    )
    await create_tables()

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

async def create_tables():
    async with pool.acquire() as connection:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT DEFAULT '📚',
                description TEXT,
                time INTEGER NOT NULL DEFAULT 10
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                a_var TEXT NOT NULL,
                b_var TEXT NOT NULL,
                c_var TEXT NOT NULL,
                d_var TEXT NOT NULL,
                answer CHAR(1) NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D')),
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                full_name TEXT,
                username TEXT,
                category TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                questions_count INTEGER NOT NULL,
                correct_answers_count INTEGER NOT NULL,
                correct_answers_percent INTEGER NOT NULL,
                spent_time TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

async def get_db():
    async with pool.acquire() as connection:
        yield connection

@app.post("/categories/", response_model=Category, status_code=201)
async def add_category(category: CategoryCreate, db=Depends(get_db)):
    query = """
        INSERT INTO categories (name, description, emoji, time)
        VALUES ($1, $2, $3, $4)
        RETURNING id, name, description, emoji, time
    """
    try:
        record = await db.fetchrow(
            query,
            category.name,
            category.description,
            category.emoji,
            category.time
        )
        return Category(**dict(record))
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Category name already exists.")

@app.get("/categories/", response_model=List[Category])
async def get_categories(limit: int = 10, db=Depends(get_db)):
    records = await db.fetch(
        "SELECT id, name, description, emoji, time FROM categories LIMIT $1", 
        limit
    )
    return [Category(**dict(record)) for record in records]

@app.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: int, db=Depends(get_db)):
    record = await db.fetchrow(
        "SELECT id, name, description, emoji, time FROM categories WHERE id = $1",
        category_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Category not found.")
    return Category(**dict(record))

@app.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, db=Depends(get_db)):
    result = await db.execute("DELETE FROM categories WHERE id = $1", category_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Category not found.")

@app.post("/questions/", response_model=Question, status_code=201)
async def add_question(question: QuestionCreate, db=Depends(get_db)):
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", question.category_id)
    if not category_exists:
        raise HTTPException(status_code=400, detail="Category does not exist.")
    
    query = """
        INSERT INTO questions (question, a_var, b_var, c_var, d_var, answer, category_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, question, a_var, b_var, c_var, d_var, answer, category_id
    """
    try:
        record = await db.fetchrow(
            query,
            question.question,
            question.a_var,
            question.b_var,
            question.c_var,
            question.d_var,
            question.answer.upper(),
            question.category_id
        )
        return Question(**dict(record))
    except asyncpg.CheckViolationError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.put("/questions/{question_id}", response_model=Question)
async def update_question(question_id: int, question: QuestionCreate, db=Depends(get_db)):
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", question.category_id)
    if not category_exists:
        raise HTTPException(status_code=400, detail="Category does not exist.")
    
    query = """
        UPDATE questions
        SET question = $1, a_var = $2, b_var = $3, c_var = $4, d_var = $5, answer = $6, category_id = $7
        WHERE id = $8
        RETURNING id, question, a_var, b_var, c_var, d_var, answer, category_id
    """
    try:
        record = await db.fetchrow(
            query,
            question.question,
            question.a_var,
            question.b_var,
            question.c_var,
            question.d_var,
            question.answer.upper(),
            question.category_id,
            question_id
        )
        if not record:
            raise HTTPException(status_code=404, detail="Question not found.")
        return Question(**dict(record))
    except asyncpg.CheckViolationError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: int, db=Depends(get_db)):
    result = await db.execute("DELETE FROM questions WHERE id = $1", question_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Question not found.")

@app.get("/questions/{question_id}", response_model=Question)
async def get_question(question_id: int, db=Depends(get_db)):
    record = await db.fetchrow(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE id = $1",
        question_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Question not found.")
    return Question(**dict(record))

@app.get("/categories/{category_id}/questions", response_model=List[Question])
async def get_questions_by_category(category_id: int, db=Depends(get_db)):
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", category_id)
    if not category_exists:
        raise HTTPException(status_code=404, detail="Category not found.")
    
    records = await db.fetch(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE category_id = $1",
        category_id
    )
    return [Question(**dict(record)) for record in records]

@app.post("/results", status_code=202)
async def save_result(payload: ResultPayload, db=Depends(get_db)):
    # Save to database
    query = """
        INSERT INTO results (
            telegram_id, full_name, username, category, category_id,
            questions_count, correct_answers_count, correct_answers_percent, spent_time
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """
    
    # Get category ID
    category_id = await db.fetchval(
        "SELECT id FROM categories WHERE name = $1", 
        payload.category
    )
    
    await db.execute(
        query,
        payload.telegram_id,
        payload.full_name,
        payload.username,
        payload.category,
        category_id,
        payload.questions_count,
        payload.correct_answers_count,
        payload.correct_answers_percent,
        payload.spent_time
    )

    # Send to admin
    if payload.telegram_id and payload.full_name:
        safe_name = html_escape.escape(payload.full_name)
        mention_html = f'<a href="tg://user?id={payload.telegram_id}">{safe_name}</a>'
    elif payload.full_name:
        mention_html = html_escape.escape(payload.full_name)
    else:
        mention_html = "Noma'lum foydalanuvchi"

    message = f"""
Yangi test natijasi:
👤 Foydalanuvchi: {mention_html}
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

@app.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    time_filter: str = "24h",
    category_id: Optional[int] = None,
    db=Depends(get_db)
):
    time_conditions = {
        "24h": "timestamp >= NOW() - INTERVAL '24 hours'",
        "week": "timestamp >= NOW() - INTERVAL '7 days'",
        "month": "timestamp >= DATE_TRUNC('month', CURRENT_DATE)",
        "all": "TRUE"
    }
    time_condition = time_conditions.get(time_filter, "TRUE")
    
    category_condition = "TRUE" if category_id is None else f"category_id = {category_id}"
    
    leaderboard_query = f"""
        SELECT 
            full_name,
            correct_answers_count as correct_answers,
            questions_count as total_questions,
            correct_answers_percent as percentage,
            category,
            spent_time,
            TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI') as date
        FROM results
        WHERE {time_condition} AND {category_condition}
        ORDER BY percentage DESC, correct_answers DESC
        LIMIT 100
    """
    
    records = await db.fetch(leaderboard_query)
    leaderboard_data = [LeaderboardEntry(**dict(record)) for record in records]
    
    categories = await db.fetch("SELECT id, name, emoji, time FROM categories ORDER BY name")
    categories_list = [Category(**dict(record)) for record in categories]
    
    return LeaderboardResponse(
        data=leaderboard_data,
        categories=categories_list
    )
    
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
            TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI') as date
        FROM results
        WHERE telegram_id = $1
        ORDER BY timestamp DESC
        LIMIT 1
    """
    record = await db.fetchrow(query, telegram_id)
    if not record:
        raise HTTPException(status_code=404, detail="Natijalar topilmadi")
    return dict(record)

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
            TO_CHAR(timestamp, 'YYYY-MM-DD HH24:MI') as date
        FROM results
        WHERE telegram_id = $1
        ORDER BY timestamp DESC
    """
    records = await db.fetch(query, telegram_id)
    if not records:
        raise HTTPException(status_code=404, detail="Natijalar topilmadi")
    return [dict(r) for r in records]



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1234)