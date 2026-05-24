"""
app/agents/study_planner_agent.py
───────────────────────────────────────────────────────────────────
Study Planner Agent — Generates personalised study plans,
career roadmaps, and weak-area improvement plans using Groq.

Does NOT need a PDF uploaded — pure LLM generation.
Connects to interview scores (weak topics) from the Interview Engine.

LLM: Groq  (llama-3.1-8b-instant)
"""

from __future__ import annotations

from app.services.groq_client import groq_chat


def _groq_chat(prompt: str) -> str:
    return groq_chat(prompt, temperature=0.4)


# ═════════════════════════════════════════════════════════════════════════════
# 1. WEEK-BY-WEEK STUDY PLAN
# ═════════════════════════════════════════════════════════════════════════════

def generate_study_plan(
    goal: str,
    current_level: str = "Intermediate",
    weeks_available: int = 4,
) -> str:
    """
    Generate a detailed week-by-week study plan.
    Called by POST /study/study-plan
    """
    prompt = f"""
You are an expert Study Planner Agent.

Create a detailed {weeks_available}-week study plan for:
Goal          : {goal}
Current Level : {current_level}

For EACH week provide:
- Week number and theme
- 3-5 specific topics to cover
- 2-3 recommended free resources (YouTube, docs, websites — mention names)
- 2 daily tasks (30-60 min each)
- One clear milestone / goal to hit by end of week

Rules:
- Realistic and achievable for a {current_level}-level student
- Progressive: each week builds on the previous
- Practical: include hands-on tasks, not just reading
- Mention specific resource names (e.g. "CS50 on YouTube", "official Python docs")

Strictly follow this format for EVERY week:

WEEK [N] — [Theme]
Topics   : topic1, topic2, topic3
Resources:
  - Resource 1 (link or platform)
  - Resource 2
Daily Tasks:
  - Task 1 (30 min)
  - Task 2 (30 min)
Milestone : what you can do by end of this week

---
"""
    return _groq_chat(prompt)


# ═════════════════════════════════════════════════════════════════════════════
# 2. TOPIC ROADMAP  (collaborator's /generate-roadmap)
# ═════════════════════════════════════════════════════════════════════════════

def generate_topic_roadmap(topic: str) -> str:
    """
    Beginner-to-advanced roadmap for any topic.
    Called by POST /study/generate-roadmap
    Preserves collaborator's original prompt structure.
    """
    prompt = f"""
You are an AI Study Roadmap Generator.

Create a complete learning roadmap for: {topic}

Rules:
- Beginner to advanced progression
- Step-by-step structure with clear phases
- Include important concepts per phase
- Mention free resources where possible
- Student-friendly and easy to follow

Format:

Phase 1 — Foundation (Week 1-2):
- Topic 1
- Topic 2
- Resource: ...

Phase 2 — Core Concepts (Week 3-4):
- Topic 3
- Topic 4
- Resource: ...

Phase 3 — Advanced (Week 5-6):
- Topic 5
- Topic 6
- Resource: ...

(continue until advanced level)
"""
    return _groq_chat(prompt)


# ═════════════════════════════════════════════════════════════════════════════
# 3. CAREER ROADMAP
# ═════════════════════════════════════════════════════════════════════════════

def generate_career_roadmap(
    role: str,
    current_skills: Optional[list[str]] = None,
    experience: str = "Intermediate",
) -> str:
    """
    Full career-level roadmap to land a specific job role.
    Called by POST /study/career-roadmap
    """
    skills_str = ", ".join(current_skills) if current_skills else "not specified"

    prompt = f"""
You are a Senior Career Coach helping a student land their dream job.

Target Role     : {role}
Current Skills  : {skills_str}
Experience Level: {experience}

Create a comprehensive career roadmap that includes:

1. SKILLS GAP ANALYSIS
   - Skills they have vs skills needed for {role}
   - Priority skills to learn first

2. PHASE-BY-PHASE LEARNING PLAN (3-4 phases)
   For each phase:
   - Phase name and duration
   - Skills to learn
   - Mini-projects to build
   - Resources (free, specific names)

3. PORTFOLIO PROJECTS
   - 3 project ideas that will impress recruiters for {role}
   - What each project should demonstrate

4. CERTIFICATIONS
   - Top 2-3 certs that help for {role}
   - Free vs paid options

5. INTERVIEW PREPARATION CHECKLIST
   - DSA topics (if applicable)
   - System design topics (if applicable)
   - Behavioral questions to prepare

6. REALISTIC TIMELINE
   - Estimated months to job-ready from {experience} level

Keep it actionable, specific, and motivating.
"""
    return _groq_chat(prompt)


# ═════════════════════════════════════════════════════════════════════════════
# 4. WEAK AREA IMPROVEMENT PLAN
# ═════════════════════════════════════════════════════════════════════════════

def generate_weak_area_plan(
    weak_topics: list[str],
    role: str = "Software Engineer",
) -> str:
    """
    Focused improvement plan for topics where interview scores were low.
    Called by POST /study/weak-area-plan
    Connects to SAS analytics / evaluation_agent output.
    """
    topics_str = ", ".join(weak_topics)

    prompt = f"""
You are an expert Interview Preparation Coach.

The candidate is targeting  : {role}
Weak areas from mock interviews: {topics_str}

Create a focused improvement plan for EACH weak topic.

For EACH weak topic provide:
- Why it matters for {role} interviews (1-2 sentences)
- 3 specific things to study
- 2 practice exercises (coding problem, design question, mock answer, etc.)
- 1 recommended free resource (name it specifically)
- Estimated days to improve from average to strong

Then provide a combined daily schedule to cover all weak areas efficiently.

Format:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEAK AREA: [topic name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Why it matters : ...
Study:
  1. ...
  2. ...
  3. ...
Practice:
  • Exercise 1: ...
  • Exercise 2: ...
Resource  : ...
Estimated : X days to solid understanding

(repeat for all weak topics)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMBINED DAILY SCHEDULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Morning   (30 min) : ...
Afternoon (45 min) : ...
Evening   (20 min) : ...
Weekend extra      : ...
"""
    return _groq_chat(prompt)


# ═════════════════════════════════════════════════════════════════════════════
# 5. INTERVIEW-BASED IMPROVEMENT PLAN
#    Takes scores directly from evaluation_agent output
# ═════════════════════════════════════════════════════════════════════════════

def generate_post_interview_plan(
    role: str,
    technical_score: float,
    communication_score: float,
    confidence_score: float,
    weak_topics: Optional[list[str]] = None,
) -> str:
    """
    Generates a personalised improvement plan immediately after
    an interview is completed. Uses scores from evaluation_agent.

    Called by POST /study/post-interview-plan
    """
    tech_pct  = round(technical_score * 100)
    comm_pct  = round(communication_score * 100)
    conf_pct  = round(confidence_score * 100)
    topics_str = ", ".join(weak_topics) if weak_topics else "not identified"

    # Determine focus areas
    areas = []
    if tech_pct  < 60: areas.append("technical depth")
    if comm_pct  < 60: areas.append("communication clarity")
    if conf_pct  < 60: areas.append("answer confidence")
    focus = ", ".join(areas) if areas else "maintaining strong performance"

    prompt = f"""
You are a post-interview AI coach.

The candidate just completed a mock interview for: {role}

SCORES:
- Technical    : {tech_pct}%
- Communication: {comm_pct}%
- Confidence   : {conf_pct}%
- Focus areas  : {focus}
- Weak topics  : {topics_str}

Create a personalised 2-week improvement plan based on these scores.

Structure:
1. SCORE ANALYSIS — what the scores mean, what to be proud of
2. PRIORITY IMPROVEMENTS — top 3 things to fix, in order
3. WEEK 1 PLAN — specific daily actions
4. WEEK 2 PLAN — build on week 1
5. MOCK INTERVIEW TIPS — 5 quick tips to perform better next time

Be encouraging but honest. Use the actual scores to personalise advice.
"""
    return _groq_chat(prompt)