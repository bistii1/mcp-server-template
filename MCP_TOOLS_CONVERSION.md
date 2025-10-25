# MCP Tools Conversion Guide

This document explains the conversion of FastAPI routes to MCP (Model Context Protocol) tools in the Skill Learning Coach server.

## Overview

All routes from `backend/routes.py` have been converted to MCP tools in `src/server.py`. MCP tools are designed to be called by Claude or other AI clients through the Model Context Protocol.

## Converted Tools

### USER TOOLS

#### 1. `create_user`
**Purpose:** Create a new user account

**Parameters:**
- `username` (str): Unique username
- `email` (str): Unique email address
- `learning_style` (str, optional): User's preferred learning style

**Returns:**
```json
{
  "user_id": int,
  "username": str,
  "email": str,
  "learning_style": str | null,
  "created_at": str (ISO format datetime)
}
```

**Error Handling:** Returns `{"error": "Username or email already exists"}` if duplicate found

---

#### 2. `update_user`
**Purpose:** Update a user's learning style preference

**Parameters:**
- `user_id` (int): ID of the user to update
- `learning_style` (str): New learning style preference

**Returns:**
```json
{
  "user_id": int,
  "username": str,
  "email": str,
  "learning_style": str,
  "created_at": str
}
```

**Error Handling:** Returns `{"error": "User not found"}` if user doesn't exist

---

### GOAL TOOLS

#### 3. `create_goal`
**Purpose:** Create a new learning goal with milestones

**Parameters:**
- `user_id` (int): ID of the user creating the goal
- `skill_name` (str): Name of the skill to learn
- `timeline` (int): Timeline in days
- `roadmap` (str): JSON string of milestones array. Each milestone should have `title` and optional `description`
  ```json
  [
    {"title": "Milestone 1", "description": "First milestone"},
    {"title": "Milestone 2", "description": "Second milestone"}
  ]
  ```
- `coach_notes` (str, optional): JSON string of coaching notes

**Returns:**
```json
{
  "goal_id": int,
  "confirmation": str,
  "skill_name": str,
  "timeline": int,
  "milestones_count": int
}
```

**Error Handling:** 
- Returns `{"error": "User not found"}` if user doesn't exist
- Returns `{"error": "Invalid roadmap JSON format"}` if JSON is malformed

---

#### 4. `get_context`
**Purpose:** Retrieve comprehensive context for a goal (used daily for task generation)

**Parameters:**
- `goal_id` (int): ID of the goal

**Returns:**
```json
{
  "goal_id": int,
  "skill_name": str,
  "learning_style": str | null,
  "last_completed_tasks": [
    {
      "task_id": int,
      "title": str,
      "description": str,
      "status": str,
      "completed_at": str | null
    }
  ],
  "current_incomplete_tasks": [...],
  "roadmap": [
    {
      "milestone_id": int,
      "title": str,
      "description": str,
      "order": int,
      "is_complete": bool
    }
  ],
  "coach_notes": dict | null
}
```

**Purpose in Flow:** This is called daily by the AI coach to get all necessary context to generate the next task or send a motivational update.

---

#### 5. `update_goal`
**Purpose:** Update goal details

**Parameters:**
- `goal_id` (int): ID of the goal to update
- `skill_name` (str, optional): New skill name
- `timeline` (int, optional): New timeline in days
- `coach_notes` (str, optional): Updated coach notes as JSON string

**Returns:**
```json
{
  "goal_id": int,
  "skill_name": str,
  "timeline": int,
  "coach_notes": dict | null,
  "message": str
}
```

---

#### 6. `update_milestone`
**Purpose:** Update milestone details or mark as complete

**Parameters:**
- `milestone_id` (int): ID of the milestone to update
- `title` (str, optional): New title
- `description` (str, optional): New description
- `is_complete` (bool, optional): Mark as complete/incomplete

**Returns:**
```json
{
  "milestone_id": int,
  "title": str,
  "description": str,
  "order": int,
  "is_complete": bool,
  "message": str
}
```

---

### TASK TOOLS

#### 7. `create_task`
**Purpose:** Create a new task for a goal

**Parameters:**
- `goal_id` (int): ID of the goal
- `task_title` (str): Title of the task
- `task_description` (str): Description of the task

**Returns:**
```json
{
  "task_id": int,
  "task_title": str,
  "task_description": str,
  "verification_type": str,
  "verification_content": dict,
  "milestone_id": int | null
}
```

**Notes:** 
- Automatically assigns to the first incomplete milestone
- Creates a basic verification structure (without LLM evaluation in this version)
- `verification_type` defaults to "text" but can be extended to "quiz", "photo", "video"

---

## Key Differences from Routes

1. **No HTTP Status Codes:** MCP tools return dicts with `error` keys instead of raising HTTPExceptions
2. **JSON String Parameters:** Complex parameters like `roadmap` and `coach_notes` are passed as JSON strings to be compatible with MCP's type system
3. **No Async/Await:** MCP tools are synchronous (blocking)
4. **Database Management:** Each tool manages its own database session lifecycle
5. **Response Format:** All responses are returned as dictionaries (automatically serialized to JSON by MCP)

## Database Setup

The MCP server uses the same database as the main FastAPI backend:
- Database URL from `.env` (defaults to `sqlite:///./skillapp.db`)
- Uses SQLAlchemy ORM with models from `backend/models.py`
- Session management handled per-tool with automatic cleanup

## Usage Example

### Creating a User and Goal

```python
# 1. Create user
user_response = create_user(
    username="john_doe",
    email="john@example.com",
    learning_style="visual"
)
user_id = user_response["user_id"]

# 2. Create goal with milestones
import json
roadmap = json.dumps([
    {"title": "Learn Python Basics", "description": "Variables, types, control flow"},
    {"title": "Learn Functions", "description": "Defining and calling functions"},
    {"title": "Learn OOP", "description": "Classes and objects"}
])

goal_response = create_goal(
    user_id=user_id,
    skill_name="Python for Backend Development",
    timeline=90,
    roadmap=roadmap
)
goal_id = goal_response["goal_id"]

# 3. Get context (called daily)
context = get_context(goal_id=goal_id)

# 4. Create task
task_response = create_task(
    goal_id=goal_id,
    task_title="Build a simple calculator",
    task_description="Create a Python script that adds, subtracts, multiplies, and divides"
)
```

## Environment Variables

Required `.env` file:
```
DATABASE_URL=sqlite:///./skillapp.db
# or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/skillapp_db
PORT=8000
```

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python src/server.py
```

The server will start on `http://0.0.0.0:8000` by default.

## Future Enhancements

1. **LLM Integration:** Integrate with LLMService for task verification generation
2. **File Upload Support:** Add file verification for photo/video verification types
3. **Advanced Verification:** Implement quiz generation and evaluation
4. **Error Logging:** Add comprehensive error logging and monitoring
5. **Caching:** Add caching for frequently accessed context data
