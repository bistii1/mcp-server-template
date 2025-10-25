#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import models and schemas
from models import User, Goal, Milestone, Task, Verification, VerificationAttempt, TaskStatus, VerificationType
from schemas import (
    UserCreate, UserResponse, UserUpdate,
    CreateGoalRequest, CreateGoalResponse,
    UpdateGoalRequest, UpdateGoalResponse,
    UpdateMilestoneRequest, UpdateMilestoneResponse,
    GetContextResponse, TaskSummary, MilestoneSummary,
    CreateTaskRequest, CreateTaskResponse,
    MilestoneInput
)

load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./skillapp.db")
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

mcp = FastMCP("Skill Learning Coach")

# ========== USER TOOLS ==========

@mcp.tool(description="Create a new user with username, email, and optional learning style")
def create_user(username: str, email: str, learning_style: Optional[str] = None) -> dict:
    """
    Create a new user.
    
    Args:
        username: Unique username
        email: Unique email address
        learning_style: Optional learning style preference
    
    Returns:
        User information including user_id, username, email, learning_style, created_at
    """
    db = get_db()
    try:
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return {"error": "Username or email already exists"}
        
        # Create new user
        user = User(
            username=username,
            email=email,
            learning_style=learning_style
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "learning_style": user.learning_style,
            "created_at": user.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@mcp.tool(description="Update a user's learning style")
def update_user(user_id: int, learning_style: str) -> dict:
    """
    Update a user's learning style.
    
    Args:
        user_id: ID of the user to update
        learning_style: New learning style preference
    
    Returns:
        Updated user information
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        user.learning_style = learning_style
        db.commit()
        db.refresh(user)
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "learning_style": user.learning_style,
            "created_at": user.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

# ========== GOAL TOOLS ==========

@mcp.tool(description="Create a new goal with milestones for a user")
def create_goal(
    user_id: int,
    skill_name: str,
    timeline: int,
    roadmap: str,
    coach_notes: Optional[str] = None
) -> dict:
    """
    Create a new goal with a roadmap of milestones.
    
    Args:
        user_id: ID of the user
        skill_name: Name of the skill to learn
        timeline: Timeline in days
        roadmap: JSON string of milestones (list of {title, description})
        coach_notes: Optional JSON string of coaching notes
    
    Returns:
        goal_id, confirmation message, and milestone count
    """
    db = get_db()
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Parse roadmap JSON
        try:
            roadmap_list = json.loads(roadmap) if isinstance(roadmap, str) else roadmap
        except json.JSONDecodeError:
            return {"error": "Invalid roadmap JSON format"}
        
        # Parse coach_notes
        coach_notes_dict = None
        if coach_notes:
            try:
                coach_notes_dict = json.loads(coach_notes) if isinstance(coach_notes, str) else coach_notes
            except json.JSONDecodeError:
                return {"error": "Invalid coach_notes JSON format"}
        
        # Create goal
        goal = Goal(
            user_id=user_id,
            skill_name=skill_name,
            timeline=timeline,
            coach_notes=coach_notes_dict
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # Store milestones from roadmap
        milestones = []
        for idx, milestone_input in enumerate(roadmap_list):
            milestone = Milestone(
                goal_id=goal.id,
                title=milestone_input.get("title", f"Milestone {idx + 1}"),
                description=milestone_input.get("description", ""),
                order=idx + 1
            )
            db.add(milestone)
            milestones.append(milestone)
        
        db.commit()
        
        return {
            "goal_id": goal.id,
            "confirmation": f"Goal '{skill_name}' created successfully with {len(milestones)} milestones",
            "skill_name": goal.skill_name,
            "timeline": goal.timeline,
            "milestones_count": len(milestones)
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@mcp.tool(description="Get context for a goal including progress, tasks, and roadmap")
def get_context(goal_id: int) -> dict:
    """
    Get comprehensive context for a goal.
    
    Args:
        goal_id: ID of the goal
    
    Returns:
        Goal details including last 5 completed tasks, incomplete tasks, roadmap, and coach notes
    """
    db = get_db()
    try:
        # Get goal
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return {"error": "Goal not found"}
        
        # Get last 5 completed tasks
        last_completed = db.query(Task).filter(
            Task.goal_id == goal_id,
            Task.status == TaskStatus.COMPLETE
        ).order_by(Task.completed_at.desc()).limit(5).all()
        
        # Get current incomplete tasks
        current_incomplete = db.query(Task).filter(
            Task.goal_id == goal_id,
            Task.status.in_([TaskStatus.INCOMPLETE, TaskStatus.IN_PROGRESS])
        ).order_by(Task.created_at.asc()).all()
        
        # Get all milestones (roadmap)
        milestones = db.query(Milestone).filter(
            Milestone.goal_id == goal_id
        ).order_by(Milestone.order).all()
        
        # Get user's learning style
        user = db.query(User).filter(User.id == goal.user_id).first()
        
        return {
            "goal_id": goal.id,
            "skill_name": goal.skill_name,
            "learning_style": user.learning_style if user else None,
            "last_completed_tasks": [
                {
                    "task_id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in last_completed
            ],
            "current_incomplete_tasks": [
                {
                    "task_id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in current_incomplete
            ],
            "roadmap": [
                {
                    "milestone_id": m.id,
                    "title": m.title,
                    "description": m.description,
                    "order": m.order,
                    "is_complete": m.is_complete
                }
                for m in milestones
            ],
            "coach_notes": goal.coach_notes
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@mcp.tool(description="Update goal details like skill name, timeline, or coach notes")
def update_goal(
    goal_id: int,
    skill_name: Optional[str] = None,
    timeline: Optional[int] = None,
    coach_notes: Optional[str] = None
) -> dict:
    """
    Update a goal's details.
    
    Args:
        goal_id: ID of the goal to update
        skill_name: New skill name (optional)
        timeline: New timeline in days (optional)
        coach_notes: New coach notes as JSON string (optional)
    
    Returns:
        Updated goal information
    """
    db = get_db()
    try:
        # Get goal
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return {"error": "Goal not found"}
        
        # Update fields if provided
        if skill_name is not None:
            goal.skill_name = skill_name
        if timeline is not None:
            goal.timeline = timeline
        if coach_notes is not None:
            try:
                goal.coach_notes = json.loads(coach_notes) if isinstance(coach_notes, str) else coach_notes
            except json.JSONDecodeError:
                return {"error": "Invalid coach_notes JSON format"}
        
        db.commit()
        db.refresh(goal)
        
        return {
            "goal_id": goal.id,
            "skill_name": goal.skill_name,
            "timeline": goal.timeline,
            "coach_notes": goal.coach_notes,
            "message": "Goal updated successfully"
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@mcp.tool(description="Update a milestone's details or completion status")
def update_milestone(
    milestone_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_complete: Optional[bool] = None
) -> dict:
    """
    Update a milestone's details or mark it as complete.
    
    Args:
        milestone_id: ID of the milestone to update
        title: New title (optional)
        description: New description (optional)
        is_complete: Mark as complete/incomplete (optional)
    
    Returns:
        Updated milestone information
    """
    db = get_db()
    try:
        # Get milestone
        milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
        if not milestone:
            return {"error": "Milestone not found"}
        
        # Update fields if provided
        if title is not None:
            milestone.title = title
        if description is not None:
            milestone.description = description
        if is_complete is not None:
            milestone.is_complete = is_complete
            if is_complete:
                milestone.completed_at = datetime.utcnow()
            else:
                milestone.completed_at = None
        
        db.commit()
        db.refresh(milestone)
        
        return {
            "milestone_id": milestone.id,
            "title": milestone.title,
            "description": milestone.description,
            "order": milestone.order,
            "is_complete": milestone.is_complete,
            "message": "Milestone updated successfully"
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

# ========== TASK TOOLS ==========

@mcp.tool(description="Create a new task for a goal")
def create_task(goal_id: int, task_title: str, task_description: str) -> dict:
    """
    Create a new task for a goal.
    
    Args:
        goal_id: ID of the goal
        task_title: Title of the task
        task_description: Description of the task
    
    Returns:
        task_id, task details, and verification type
    """
    db = get_db()
    try:
        # Verify goal exists
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return {"error": "Goal not found"}
        
        # Find appropriate milestone (first incomplete one)
        current_milestone = db.query(Milestone).filter(
            Milestone.goal_id == goal_id,
            Milestone.is_complete == False
        ).order_by(Milestone.order).first()
        
        # Create task
        task = Task(
            goal_id=goal_id,
            milestone_id=current_milestone.id if current_milestone else None,
            title=task_title,
            description=task_description,
            status=TaskStatus.INCOMPLETE
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Generate basic verification (without LLM for now in MCP tool)
        # In production, you could call an LLM service here
        verification_data = {
            "type": "text",
            "content": {
                "prompt": f"Please complete the following task: {task_title}",
                "guidelines": task_description
            },
            "requirements": {
                "completion_criteria": "Task should be completed according to the description"
            }
        }
        
        # Store verification
        verification = Verification(
            task_id=task.id,
            verification_type=VerificationType(verification_data.get("type", "text")),
            content=json.dumps(verification_data.get("content", {})),
            requirements=json.dumps(verification_data.get("requirements", {}))
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
        
        return {
            "task_id": task.id,
            "task_title": task.title,
            "task_description": task.description,
            "verification_type": verification.verification_type.value,
            "verification_content": verification_data.get("content", {}),
            "milestone_id": current_milestone.id if current_milestone else None
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting Skill Learning Coach MCP server on {host}:{port}")
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )
