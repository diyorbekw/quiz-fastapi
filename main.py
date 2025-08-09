from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncpg
from asyncpg.pool import Pool
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

app = FastAPI(title="Quiz API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/quizdb")

# Models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

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
    pool = await asyncpg.create_pool(DATABASE_URL)
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
@app.post("/categories/", response_model=Category, status_code=201)
async def add_category(category: CategoryCreate, db=Depends(get_db)):
    """Add a new category to the database"""
    query = """
        INSERT INTO categories (name, description)
        VALUES ($1, $2)
        RETURNING id, name, description
    """
    try:
        record = await db.fetchrow(query, category.name, category.description)
        return Category(**record)
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Category name already exists")

@app.get("/categories/", response_model=List[Category])
async def get_categories(limit: int = 10, db=Depends(get_db)):
    """Get list of categories with limit"""
    records = await db.fetch("SELECT id, name, description FROM categories LIMIT $1", limit)
    return [Category(**record) for record in records]

@app.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: int, db=Depends(get_db)):
    """Get a specific category by ID"""
    record = await db.fetchrow(
        "SELECT id, name, description FROM categories WHERE id = $1",
        category_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Category not found")
    return Category(**record)

@app.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, db=Depends(get_db)):
    """Delete a category (will cascade to related questions due to ON DELETE CASCADE)"""
    result = await db.execute("DELETE FROM categories WHERE id = $1", category_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Category not found")

# Question Endpoints
@app.post("/questions/", response_model=Question, status_code=201)
async def add_question(question: QuestionCreate, db=Depends(get_db)):
    """Add a new question to the database"""
    # First check if category exists
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", question.category_id)
    if not category_exists:
        raise HTTPException(status_code=400, detail="Category does not exist")
    
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
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D")

@app.put("/questions/{question_id}", response_model=Question)
async def change_question(question_id: int, question: QuestionCreate, db=Depends(get_db)):
    """Update an existing question"""
    # Check if new category exists
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", question.category_id)
    if not category_exists:
        raise HTTPException(status_code=400, detail="Category does not exist")
    
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
            raise HTTPException(status_code=404, detail="Question not found")
        return Question(**record)
    except asyncpg.CheckViolationError:
        raise HTTPException(status_code=400, detail="Answer must be A, B, C or D")

@app.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: int, db=Depends(get_db)):
    """Delete a question"""
    result = await db.execute("DELETE FROM questions WHERE id = $1", question_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Question not found")
        return
    
    return {"message": "Question deleted successfully"}


@app.get("/questions/{question_id}", response_model=Question)
async def get_question(question_id: int, db=Depends(get_db)):
    """Get a specific question by ID"""
    record = await db.fetchrow(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE id = $1",
        question_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="Question not found")
    return Question(**record)

@app.get("/categories/{category_id}/questions", response_model=List[Question])
async def get_questions_by_category(category_id: int, db=Depends(get_db)):
    """Get all questions for a specific category"""
    # First check if category exists
    category_exists = await db.fetchval("SELECT 1 FROM categories WHERE id = $1", category_id)
    if not category_exists:
        raise HTTPException(status_code=404, detail="Category not found")
    
    records = await db.fetch(
        "SELECT id, question, a_var, b_var, c_var, d_var, answer, category_id FROM questions WHERE category_id = $1",
        category_id
    )
    return [Question(**record) for record in records]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)