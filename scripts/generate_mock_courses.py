"""
Mock Course Generator for Tamkeen Recommendation System
========================================================
Generates 50+ mock courses using template-based automation to make the
recommendation engine produce meaningful, intelligent suggestions.

Strategy:
  - 7 real topics × 5 templates = 35 templated courses
  - 15 cross-domain courses
  - Total: 50 courses (all marked is_mock=true)

Output:
  - out_small/mock_courses.csv     (CSV for engine consumption)
  - out_small/mock_courses.json    (JSON for reference / frontend)
  - out_small/courses.csv          (merged: 7 real + 50 mock)
"""

import csv
import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path to import generators
SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from data_generators.courses import generate_lessons
from data_generators.assessments import generate_assessments
from data_generators.features import build_user_features, build_course_features, export_parquet
from data_generators.recommendations import simulate_recommendation_exposures

# ─── Configuration ──────────────────────────────────────────────────────────────

REAL_TOPICS = [
    {
        "key": "python",
        "label": "Python",
        "category": "programming",
        "skills": ["programming", "backend", "scripting", "python"],
        "base_difficulty": 3,
    },
    {
        "key": "ux",
        "label": "UX Design",
        "category": "design",
        "skills": ["design", "user-research", "prototyping", "ux"],
        "base_difficulty": 2,
    },
    {
        "key": "testing",
        "label": "Software Testing",
        "category": "qa",
        "skills": ["qa", "automation", "debugging", "testing"],
        "base_difficulty": 3,
    },
    {
        "key": "iot",
        "label": "IoT Development",
        "category": "hardware",
        "skills": ["hardware", "embedded", "electronics", "iot"],
        "base_difficulty": 4,
    },
    {
        "key": "embedded",
        "label": "Emaded (Entrepreneurship)",
        "category": "business",
        "skills": ["entrepreneurship", "business", "marketing", "startup"],
        "base_difficulty": 2,
    },
    {
        "key": "digital_marketing",
        "label": "Digital Marketing",
        "category": "marketing",
        "skills": ["marketing", "seo", "social-media", "advertising"],
        "base_difficulty": 2,
    },
    {
        "key": "freelancing_khamsat",
        "label": "Freelancing with Khamsat",
        "category": "business",
        "skills": ["freelancing", "client-management", "communication", "negotiation"],
        "base_difficulty": 2,
    },
]

TEMPLATES = [
    {
        "suffix": "advanced",
        "title_fmt": "Advanced {label}",
        "desc_fmt": "[MOCK] Master advanced {label} techniques and real-world best practices",
        "difficulty_delta": +1,
        "tags_extra": ["advanced", "professional", "expert"],
    },
    {
        "suffix": "fundamentals",
        "title_fmt": "{label} Fundamentals",
        "desc_fmt": "[MOCK] Learn {label} from scratch with beginner-friendly exercises",
        "difficulty_delta": -2,
        "tags_extra": ["beginner", "fundamentals", "introduction"],
    },
    {
        "suffix": "projects",
        "title_fmt": "{label} Real-World Projects",
        "desc_fmt": "[MOCK] Build practical, portfolio-ready projects with {label}",
        "difficulty_delta": 0,
        "tags_extra": ["projects", "practical", "hands-on"],
    },
    {
        "suffix": "professional",
        "title_fmt": "Professional {label}",
        "desc_fmt": "[MOCK] Industry practices, workflows, and career skills for {label}",
        "difficulty_delta": +1,
        "tags_extra": ["professional", "industry", "career"],
    },
    {
        "suffix": "tools",
        "title_fmt": "Essential {label} Tools",
        "desc_fmt": "[MOCK] Master the essential tools and frameworks used in {label}",
        "difficulty_delta": -1,
        "tags_extra": ["tools", "frameworks", "ecosystem"],
    },
]

CROSS_DOMAIN_COURSES = [
    {
        "id": "fullstack_web",
        "title": "Full Stack Web Development",
        "description": "[MOCK] Build complete web applications from frontend to backend",
        "category": "programming",
        "difficulty": 4,
        "tags": ["fullstack", "web", "frontend", "backend"],
        "related_to": ["python", "ux", "testing"],
        "skills": ["programming", "backend", "frontend", "web-development"],
        "duration_hours": 40.0,
        "rating": 4.6,
    },
    {
        "id": "data_science_python",
        "title": "Data Science with Python",
        "description": "[MOCK] Analyze data, build models, and create visualizations with Python",
        "category": "data",
        "difficulty": 3,
        "tags": ["data-science", "python", "analytics", "machine-learning"],
        "related_to": ["python"],
        "skills": ["data-analysis", "python", "statistics", "visualization"],
        "duration_hours": 35.0,
        "rating": 4.5,
    },
    {
        "id": "mobile_app_dev",
        "title": "Mobile App Development",
        "description": "[MOCK] Design and develop native and cross-platform mobile applications",
        "category": "programming",
        "difficulty": 3,
        "tags": ["mobile", "app-development", "cross-platform", "ui"],
        "related_to": ["python", "ux"],
        "skills": ["mobile-development", "programming", "ui-design"],
        "duration_hours": 30.0,
        "rating": 4.3,
    },
    {
        "id": "cloud_computing",
        "title": "Cloud Computing & Deployment",
        "description": "[MOCK] Deploy, scale, and manage applications on cloud platforms",
        "category": "programming",
        "difficulty": 4,
        "tags": ["cloud", "devops", "deployment", "aws"],
        "related_to": ["python", "iot"],
        "skills": ["cloud", "devops", "infrastructure", "deployment"],
        "duration_hours": 25.0,
        "rating": 4.4,
    },
    {
        "id": "ai_ml_basics",
        "title": "AI & Machine Learning Basics",
        "description": "[MOCK] Introduction to artificial intelligence and machine learning concepts",
        "category": "data",
        "difficulty": 3,
        "tags": ["ai", "machine-learning", "deep-learning", "python"],
        "related_to": ["python"],
        "skills": ["ai", "machine-learning", "python", "data-science"],
        "duration_hours": 28.0,
        "rating": 4.7,
    },
    {
        "id": "database_design",
        "title": "Database Design & SQL",
        "description": "[MOCK] Design efficient databases and write powerful SQL queries",
        "category": "programming",
        "difficulty": 2,
        "tags": ["database", "sql", "data-modeling", "backend"],
        "related_to": ["python", "testing"],
        "skills": ["database", "sql", "data-modeling", "backend"],
        "duration_hours": 18.0,
        "rating": 4.2,
    },
    {
        "id": "git_version_control",
        "title": "Version Control & Git",
        "description": "[MOCK] Master Git workflows, branching strategies, and team collaboration",
        "category": "programming",
        "difficulty": 1,
        "tags": ["git", "version-control", "collaboration", "devops"],
        "related_to": ["python", "testing"],
        "skills": ["git", "collaboration", "version-control"],
        "duration_hours": 8.0,
        "rating": 4.5,
    },
    {
        "id": "docker_containers",
        "title": "Docker & Containerization",
        "description": "[MOCK] Package and deploy applications using Docker containers",
        "category": "programming",
        "difficulty": 3,
        "tags": ["docker", "containers", "devops", "microservices"],
        "related_to": ["python", "cloud_computing"],
        "skills": ["docker", "devops", "containerization"],
        "duration_hours": 15.0,
        "rating": 4.4,
    },
    {
        "id": "startup_guide",
        "title": "Startup Guide: From Idea to Launch",
        "description": "[MOCK] A complete roadmap for turning your idea into a successful startup",
        "category": "business",
        "difficulty": 2,
        "tags": ["startup", "entrepreneurship", "business-plan", "funding"],
        "related_to": ["embedded", "freelancing_khamsat"],
        "skills": ["entrepreneurship", "business-planning", "leadership"],
        "duration_hours": 20.0,
        "rating": 4.3,
    },
    {
        "id": "content_marketing",
        "title": "Content Marketing Strategy",
        "description": "[MOCK] Create compelling content that drives engagement and conversions",
        "category": "marketing",
        "difficulty": 2,
        "tags": ["content-marketing", "copywriting", "seo", "strategy"],
        "related_to": ["digital_marketing"],
        "skills": ["content-creation", "marketing", "seo", "copywriting"],
        "duration_hours": 14.0,
        "rating": 4.1,
    },
    {
        "id": "personal_branding",
        "title": "Personal Branding for Professionals",
        "description": "[MOCK] Build a strong personal brand and grow your professional network",
        "category": "business",
        "difficulty": 1,
        "tags": ["personal-branding", "networking", "career", "social-media"],
        "related_to": ["freelancing_khamsat", "digital_marketing"],
        "skills": ["branding", "networking", "communication"],
        "duration_hours": 10.0,
        "rating": 4.0,
    },
    {
        "id": "robotics_hardware",
        "title": "Robotics & Hardware Engineering",
        "description": "[MOCK] Design and build robots using sensors, actuators, and microcontrollers",
        "category": "hardware",
        "difficulty": 5,
        "tags": ["robotics", "hardware", "electronics", "embedded-systems"],
        "related_to": ["iot"],
        "skills": ["robotics", "hardware", "electronics", "embedded"],
        "duration_hours": 45.0,
        "rating": 4.2,
    },
    {
        "id": "web_design_frontend",
        "title": "Web Design & Frontend Development",
        "description": "[MOCK] Create beautiful, responsive websites with HTML, CSS, and JavaScript",
        "category": "design",
        "difficulty": 2,
        "tags": ["web-design", "frontend", "html", "css", "javascript"],
        "related_to": ["ux", "python"],
        "skills": ["web-design", "frontend", "html-css", "javascript"],
        "duration_hours": 22.0,
        "rating": 4.5,
    },
    {
        "id": "figma_designers",
        "title": "Figma for Designers",
        "description": "[MOCK] Master Figma for UI/UX design, prototyping, and team collaboration",
        "category": "design",
        "difficulty": 2,
        "tags": ["figma", "ui-design", "prototyping", "design-tools"],
        "related_to": ["ux"],
        "skills": ["figma", "ui-design", "prototyping", "design"],
        "duration_hours": 12.0,
        "rating": 4.6,
    },
    {
        "id": "advanced_ux_research",
        "title": "Advanced UX Research Methods",
        "description": "[MOCK] Conduct in-depth user research with advanced methodologies",
        "category": "design",
        "difficulty": 4,
        "tags": ["ux-research", "user-testing", "analytics", "methodology"],
        "related_to": ["ux"],
        "skills": ["ux-research", "user-testing", "data-analysis"],
        "duration_hours": 16.0,
        "rating": 4.3,
    },
]


# ─── Generator Class ────────────────────────────────────────────────────────────

class MockCourseGenerator:
    """Generate mock courses using template-based expansion."""

    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.courses = []
        self._next_id = 1001
        self._generate_templated_courses()
        self._generate_cross_domain_courses()

    def _clamp_difficulty(self, val: int) -> int:
        return max(1, min(5, val))

    def _gen_duration(self, difficulty: int) -> float:
        """Generate realistic duration based on difficulty."""
        base = {1: 6, 2: 12, 3: 20, 4: 30, 5: 40}
        return round(max(2.0, np.random.normal(base[difficulty], base[difficulty] * 0.3)), 2)

    def _gen_rating(self) -> float:
        return round(np.clip(np.random.normal(4.2, 0.4), 2.5, 5.0), 2)

    def _gen_completion_rate(self, difficulty: int) -> float:
        base = {1: 0.82, 2: 0.75, 3: 0.65, 4: 0.55, 5: 0.45}
        return round(np.clip(np.random.normal(base[difficulty], 0.08), 0.2, 0.95), 3)

    def _generate_templated_courses(self):
        """Generate courses from topic × template combinations."""
        for topic in REAL_TOPICS:
            for tmpl in TEMPLATES:
                difficulty = self._clamp_difficulty(topic["base_difficulty"] + tmpl["difficulty_delta"])
                course_id = f"mock_{topic['key']}_{tmpl['suffix']}"
                title = tmpl["title_fmt"].format(label=topic["label"])
                description = tmpl["desc_fmt"].format(label=topic["label"])
                tags = list(set(topic["skills"][:2] + tmpl["tags_extra"]))
                
                self.courses.append({
                    "course_id": course_id,
                    "title": title,
                    "description": description,
                    "category": topic["category"],
                    "difficulty_level": difficulty,
                    "duration_hours": self._gen_duration(difficulty),
                    "rating": self._gen_rating(),
                    "completion_rate": self._gen_completion_rate(difficulty),
                    "tags": json.dumps(tags),
                    "is_mock": True,
                    "related_to": json.dumps([topic["key"]]),
                    "skills": json.dumps(topic["skills"]),
                })
                self._next_id += 1

    def _generate_cross_domain_courses(self):
        """Add the 15 pre-defined cross-domain courses."""
        for cd in CROSS_DOMAIN_COURSES:
            difficulty = cd["difficulty"]
            self.courses.append({
                "course_id": f"mock_{cd['id']}",
                "title": cd["title"],
                "description": cd["description"],
                "category": cd["category"],
                "difficulty_level": difficulty,
                "duration_hours": cd["duration_hours"],
                "rating": cd["rating"],
                "completion_rate": self._gen_completion_rate(difficulty),
                "tags": json.dumps(cd["tags"]),
                "is_mock": True,
                "related_to": json.dumps(cd["related_to"]),
                "skills": json.dumps(cd["skills"]),
            })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.courses)

    def to_csv(self, path: str):
        """Export mock courses to CSV."""
        df = self.to_dataframe()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        df.to_csv(path, index=False)
        print(f"  [OK] Wrote {len(df)} mock courses -> {path}")
        return df

    def to_json(self, path: str):
        """Export mock courses to JSON."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.courses, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Wrote {len(self.courses)} mock courses -> {path}")


# ─── Merge with Real Courses ────────────────────────────────────────────────────

def merge_courses(real_csv: str, mock_csv: str, output_csv: str):
    """Merge real courses CSV with mock courses CSV into a single file."""
    real_df = pd.read_csv(real_csv)
    mock_df = pd.read_csv(mock_csv)
    
    # Add missing columns to real courses for compatibility
    if "is_mock" not in real_df.columns:
        real_df["is_mock"] = False
    if "tags" not in real_df.columns:
        real_df["tags"] = "[]"
    if "related_to" not in real_df.columns:
        real_df["related_to"] = "[]"
    if "skills" not in real_df.columns:
        real_df["skills"] = "[]"
    if "title" not in real_df.columns:
        real_df["title"] = real_df["course_id"].str.replace("_", " ").str.title()
    if "description" not in real_df.columns:
        real_df["description"] = real_df["title"].apply(lambda t: f"Learn {t} on Tamkeen platform")
    
    # Ensure both DataFrames have the same columns
    all_cols = list(dict.fromkeys(list(real_df.columns) + list(mock_df.columns)))
    for col in all_cols:
        if col not in real_df.columns:
            real_df[col] = ""
        if col not in mock_df.columns:
            mock_df[col] = ""
    
    merged = pd.concat([real_df, mock_df], ignore_index=True)
    merged.to_csv(output_csv, index=False)
    print(f"  [OK] Merged {len(real_df)} real + {len(mock_df)} mock = {len(merged)} total -> {output_csv}")
    return merged


# ─── Generate Synthetic Interactions for Mock Courses ────────────────────────────

def generate_mock_interactions(merged_courses_df: pd.DataFrame, users_csv: str,
                                output_dir: str, seed: int = 42):
    """
    Generate synthetic interaction events for mock courses so the recommendation
    engine has collaborative filtering signal for the new courses.
    """
    np.random.seed(seed)
    users_df = pd.read_csv(users_csv)
    
    mock_courses = merged_courses_df[merged_courses_df["is_mock"] == True]["course_id"].tolist()
    user_ids = users_df["user_id"].tolist()
    
    event_types = ["view_course", "click_course", "enroll_course",
                   "video_play", "complete_lesson", "rate_course", "complete_course"]
    event_probs = [0.30, 0.20, 0.15, 0.15, 0.10, 0.05, 0.05]
    
    # Tier-based interaction intensity
    tier_intensity = {"dormant": 2, "casual": 5, "regular": 8, "power": 12}
    
    rows = []
    base_date = datetime(2026, 4, 22)
    
    for _, user in users_df.iterrows():
        uid = user["user_id"]
        tier = user["activity_tier"]
        n_interactions = tier_intensity.get(tier, 5)
        
        # Each user interacts with a subset of mock courses
        n_courses = min(len(mock_courses), max(2, int(n_interactions * 1.5)))
        selected_courses = np.random.choice(mock_courses, size=n_courses, replace=False)
        
        for cid in selected_courses:
            n_events = np.random.randint(1, n_interactions + 1)
            for _ in range(n_events):
                event = np.random.choice(event_types, p=event_probs)
                ts = base_date - timedelta(
                    hours=np.random.randint(0, 168),
                    minutes=np.random.randint(0, 60)
                )
                value = ""
                if event == "rate_course":
                    value = json.dumps({"rating": int(np.random.choice([3, 4, 5], p=[0.2, 0.4, 0.4]))})
                elif event == "video_play":
                    value = json.dumps({"duration_seconds": np.random.randint(60, 1200)})
                
                rows.append({
                    "user_id": uid,
                    "course_id": cid,
                    "lesson_id": "",
                    "event_type": event,
                    "event_ts": ts.isoformat(),
                    "value": value,
                })
    
    interactions_df = pd.DataFrame(rows)
    
    # Partition by date
    interactions_df["__date"] = pd.to_datetime(interactions_df["event_ts"]).dt.date
    for date, part in interactions_df.groupby("__date"):
        out_path = os.path.join(output_dir, f"part-{date}.csv")
        if os.path.exists(out_path):
            # Append to existing partition
            existing = pd.read_csv(out_path)
            combined = pd.concat([existing, part.drop(columns=["__date"])], ignore_index=True)
            combined.to_csv(out_path, index=False)
        else:
            part.drop(columns=["__date"]).to_csv(out_path, index=False)
    
    print(f"  [OK] Generated {len(interactions_df)} mock interactions across {interactions_df['__date'].nunique()} days")
    return interactions_df


# ─── Generate Stub Embeddings ────────────────────────────────────────────────────

def generate_stub_embeddings(merged_courses_csv: str, embeddings_dir: str, dim: int = 16):
    """
    Generate stub embeddings for all courses (real + mock).
    Uses random vectors with category-based clustering so similar courses
    have similar embeddings.
    """
    np.random.seed(42)
    courses_df = pd.read_csv(merged_courses_csv)
    n_courses = len(courses_df)
    
    # Create category centroids for more realistic embeddings
    categories = courses_df["category"].unique()
    category_centroids = {cat: np.random.normal(0, 1, dim) for cat in categories}
    
    embeddings = np.zeros((n_courses, dim))
    for i, (_, course) in enumerate(courses_df.iterrows()):
        centroid = category_centroids.get(course["category"], np.zeros(dim))
        noise = np.random.normal(0, 0.3, dim)
        embeddings[i] = centroid + noise
    
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    os.makedirs(embeddings_dir, exist_ok=True)
    out_path = os.path.join(embeddings_dir, "course_text.npy")
    np.save(out_path, embeddings)
    print(f"  [OK] Generated embeddings ({n_courses} x {dim}) -> {out_path}")
    return embeddings


# ─── Main Entry Point ───────────────────────────────────────────────────────────

def main():
    project_root = Path(__file__).resolve().parent.parent
    out_dir = project_root / "out_small"
    config_path = project_root / "config" / "synthetic_config_small.yaml"
    
    import yaml
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    print("=" * 60)
    print("  Tamkeen Full-Stack Mock Generator")
    print("=" * 60)
    print()
    
    # Step 1: Generate mock courses
    print("[STEP 1] Generating mock courses...")
    generator = MockCourseGenerator(seed=42)
    mock_csv = str(out_dir / "mock_courses.csv")
    mock_json = str(out_dir / "mock_courses.json")
    generator.to_csv(mock_csv)
    generator.to_json(mock_json)
    
    mock_df = generator.to_dataframe()
    print(f"   -> {len(mock_df)} mock courses generated")
    print()
    
    # Step 2: Merge with real courses
    print("[STEP 2] Merging with real courses...")
    backup_csv = str(out_dir / "courses_original_7.csv")
    if not os.path.exists(backup_csv):
        import shutil
        shutil.copy2(str(out_dir / "courses.csv"), backup_csv)
        print(f"   -> Backed up original courses -> {backup_csv}")
    
    merged_csv = str(out_dir / "courses.csv")
    merged_df = merge_courses(backup_csv, mock_csv, merged_csv)
    print()
    
    # Step 3: Generate lessons for all courses
    print("[STEP 3] Generating lessons for entire catalog...")
    lessons_df = generate_lessons(merged_df)
    lessons_df.to_csv(out_dir / "lessons.csv", index=False)
    print(f"   -> [OK] Generated {len(lessons_df)} lessons total")
    print()
    
    # Step 4: Generate assessments and questions
    print("[STEP 4] Generating assessments and questions...")
    assessments_df, questions_df = generate_assessments(config, merged_df, seed=42)
    assessments_df.to_csv(out_dir / "assessments.csv", index=False)
    questions_df.to_csv(out_dir / "questions.csv", index=False)
    print(f"   -> [OK] Generated {len(assessments_df)} assessments and {len(questions_df)} questions")
    print()
    
    # Step 5: Generate synthetic interactions for mock courses
    print("[STEP 5] Generating synthetic interactions for mock courses...")
    interactions_dir = str(out_dir / "interactions")
    interactions_df = generate_mock_interactions(merged_df, str(out_dir / "users.csv"), interactions_dir, seed=42)
    print()
    
    # Step 6: Generate recommendation exposures
    print("[STEP 6] Simulating recommendation exposures...")
    users_df = pd.read_csv(out_dir / "users.csv")
    recs_df = simulate_recommendation_exposures(config, users_df, merged_df, seed=42)
    recs_dir = out_dir / "recommendation_exposures"
    os.makedirs(recs_dir, exist_ok=True)
    
    # Partition recs
    recs_df["__date"] = pd.to_datetime(recs_df["exposed_at"]).dt.date
    for date, part in recs_df.groupby("__date"):
        part.drop(columns=["__date"]).to_csv(recs_dir / f"part-{date}.csv", index=False)
    print(f"   -> [OK] Generated {len(recs_df)} recommendation exposures")
    print()
    
    # Step 7: Update feature store
    print("[STEP 7] Building feature store snapshots...")
    # We need to reload the full interactions for correct feature building
    interactions_parts = []
    for file in os.listdir(interactions_dir):
        if file.endswith(".csv"):
            interactions_parts.append(pd.read_csv(os.path.join(interactions_dir, file)))
    full_interactions_df = pd.concat(interactions_parts, ignore_index=True)
    
    # Parse JSON values for feature builder
    def safe_json_load(v):
        if not v or pd.isna(v) or v == "": return {}
        try:
            return json.loads(v) if isinstance(v, str) else v
        except: return {}
    full_interactions_df['value'] = full_interactions_df['value'].apply(safe_json_load)
    
    user_features_df = build_user_features(users_df, full_interactions_df, config)
    course_features_df = build_course_features(merged_df, full_interactions_df, config)
    
    os.makedirs(out_dir / "feature_store", exist_ok=True)
    export_parquet(user_features_df, str(out_dir / "feature_store" / "users.parquet"))
    export_parquet(course_features_df, str(out_dir / "feature_store" / "courses.parquet"))
    print("   -> [OK] Updated feature store parquets")
    print()
    
    # Step 8: Regenerate embeddings for all courses
    print("[STEP 8] Generating embeddings for expanded catalog...")
    embeddings_dir = str(out_dir / "embeddings")
    generate_stub_embeddings(merged_csv, embeddings_dir, dim=16)
    print()
    
    # Summary
    print("=" * 60)
    print("  COMPLETE - SYSTEM IS FULLY CONSISTENT!")
    print("=" * 60)
    print()
    print(f"  Summary:")
    print(f"  --------")
    print(f"  Total Courses:    {len(merged_df)}")
    print(f"  Total Lessons:    {len(lessons_df)}")
    print(f"  Total Assessments: {len(assessments_df)}")
    print(f"  Interactions:     {len(full_interactions_df)}")
    print()
    print("  The entire out_small directory has been synchronized.")
    print("  Next step: Start the API server and demo with confidence!")
    print()


if __name__ == "__main__":
    main()
