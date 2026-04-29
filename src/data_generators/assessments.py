import numpy as np
import pandas as pd
from data_generators.utils import generate_id

def generate_assessments(config, courses_df, seed=42):
    np.random.seed(seed)
    mean_assess = config['assessments']['per_course_mean']
    rows = []
    questions = []
    assess_idx = 0
    question_idx = 0
    for _, c in courses_df.iterrows():
        n_assess = max(1, int(np.random.poisson(mean_assess)))
        for j in range(n_assess):
            assessment_id = generate_id("assessment", assess_idx)
            assess_idx += 1
            type_ = np.random.choice(["quiz","exam","practice"], p=[0.6,0.2,0.2])
            rows.append({
                "assessment_id": assessment_id,
                "course_id": c.course_id,
                "title": f"{c.course_id} Assessment {j+1}",
                "type": type_,
                "passing_score": np.random.randint(50, 80),
                "time_limit_minutes": np.random.choice([10,20,30,45,60]),
                "max_attempts": np.random.choice([1,2,3,5])
            })
            # Questions
            q_count = max(5, int(np.random.poisson(config['assessments']['questions_per_assessment_mean'])))
            for q in range(q_count):
                question_id = generate_id("question", question_idx)
                question_idx += 1
                difficulty_level = np.random.choice([1,2,3,4,5], p=[0.1,0.2,0.4,0.2,0.1])
                question_type = np.random.choice(["multiple_choice","true_false"], p=[0.8,0.2])
                correct_answer = "A"
                options = ["A","B","C","D"] if question_type == "multiple_choice" else ["True","False"]
                questions.append({
                    "question_id": question_id,
                    "assessment_id": assessment_id,
                    "question_text": f"Sample question {question_id}",
                    "question_type": question_type,
                    "correct_answer": correct_answer,
                    "options": "|".join(options),
                    "difficulty_level": difficulty_level
                })
    return pd.DataFrame(rows), pd.DataFrame(questions)