from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncpg
from asyncpg.pool import Pool
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import ssl

# Load environment variables
load_dotenv()

app = FastAPI(title="Quiz API", version="1.0", description="API for managing quiz questions and categories")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection settings
DATABASE_URL = "postgresql://postgres:gezher-jefxox-9myTxi@db.abkgeaijjryrdlaghflp.supabase.co:5432/postgres"

# Models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    emoji: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        orm_mode = True

class QuestionBase(BaseModel):
    question: str
    a_var: str
    b_var: str
    c_var: str
    d_var: str
    answer: str  # 'A', 'B', 'C' or 'D'
    category_id: int

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int

    class Config:
        orm_mode = True

# Database connection pool
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
        # Create categories table first
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                emoji TEXT,
                description TEXT
            )
        """)
        
        # Then create questions table with foreign key
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

async def get_db():
    async with pool.acquire() as connection:
        yield connection

# Category Endpoints
@app.post("/categories/", response_model=Category, status_code=201, summary="Add a new category")
async def add_category(category: CategoryCreate, db=Depends(get_db)):
    query = """
        INSERT INTO categories (name, description, emoji)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, emoji
    """
    try:
        record = await db.fetchrow(query, category.name, category.description, category.emoji)
        return Category(**record)
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Category name already exists.")

@app.get("/categories/", response_model=List[Category], summary="Get list of categories")
async def get_categories(limit: int = 10, db=Depends(get_db)):

    records = await db.fetch("SELECT id, name, description, emoji FROM categories LIMIT $1", limit)
    return [Category(**record) for record in records]

@app.get("/categories/{category_id}", response_model=Category, summary="Get a specific category ")
async def get_category(category_id: int, db=Depends(get_db)):
    record = await db.fetchrow(
        "SELECT id, name, description, emoji FROM categories WHERE id = $1",
        category_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Category not found.")
    return Category(**record)

@app.delete("/categories/{category_id}", status_code=204, summary="Delete a category")
async def delete_category(category_id: int, db=Depends(get_db)):
    result = await db.execute("DELETE FROM categories WHERE id = $1", category_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Category not found.")

# Question Endpoints
@app.post("/questions/", response_model=Question, status_code=201, summary="Add a new question")
async def add_question(question: QuestionCreate, db=Depends(get_db)):
    # First check if category exists
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
        return Question(**record)
    except asyncpg.CheckViolationError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.put("/questions/{question_id}", response_model=Question, summary="Update a question")
async def change_question(question_id: int, question: QuestionCreate, db=Depends(get_db)):
    # Check if new category exists
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
        return Question(**record)
    except asyncpg.CheckViolationError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D.")

@app.delete("/questions/{question_id}", status_code=204, summary="Delete a question")
async def delete_question(question_id: int, db=Depends(get_db)):
    result = await db.execute("DELETE FROM questions WHERE id = $1", question_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Question not found.")
        return
    
    return {"message": "Question deleted successfully."}


@app.get("/questions/{question_id}", response_model=Question, summary="Get a specific question")
async def get_question(question_id: int, db=Depends(get_db)):
    record = await db.fetchrow(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE id = $1",
        question_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Question not found.")
    return Question(**record)

@app.get("/categories/{category_id}/questions", response_model=List[Question], summary="Get questions by category")
async def get_questions_by_category(category_id: int, db=Depends(get_db)):
    # First check if category exists
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", category_id)
    if not category_exists:
        raise HTTPException(status_code=404, detail="Category not found.")
    
    records = await db.fetch(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE category_id = $1",
        category_id
    )
    return [Question(**record) for record in records]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)