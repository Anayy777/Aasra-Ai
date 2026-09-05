from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_skill_similarity(user_skills, course_skills):
    """
    Calculate similarity between beneficiary skills
    and course skills using TF-IDF + cosine similarity.
    """

    if not user_skills or not course_skills:
        return 0.0

    user_text = " ".join(user_skills)
    course_text = " ".join(course_skills)

    documents = [user_text, course_text]

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform(documents)

    similarity = cosine_similarity(
        vectors[0],
        vectors[1]
    )[0][0]

    return float(similarity)

