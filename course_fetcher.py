"""
course_fetcher.py
-----------------
Fetches *courses* from a static curated list of free educational platforms.

Why static lists?
    Many great course sites (MIT OCW, Khan Academy, freeCodeCamp) do not offer
    a free public search API. A curated list is reliable, works offline from
    APIs, and is easy for beginners to extend — just add another dict below.

Each entry is normalized to LearningResource with resource_type="course".
"""

from schemas import LearningResource

# ---------------------------------------------------------------------------
# Curated free courses — add your own rows anytime
# ---------------------------------------------------------------------------
CURATED_COURSES: list[dict] = [
    {
        "title": "CS50: Introduction to Computer Science",
        "description": "Harvard's famous intro course covering C, Python, web, and CS fundamentals.",
        "url": "https://cs50.harvard.edu/x/",
        "source": "Harvard / edX (free audit)",
        "difficulty": "beginner",
        "tags": ["computer-science", "python", "c", "programming", "algorithms"],
    },
    {
        "title": "MIT 6.006 Introduction to Algorithms",
        "description": "Classic algorithms course: sorting, graphs, dynamic programming, and more.",
        "url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/",
        "source": "MIT OpenCourseWare",
        "difficulty": "intermediate",
        "tags": ["algorithms", "data-structures", "computer-science"],
    },
    {
        "title": "freeCodeCamp Full Stack Curriculum",
        "description": "Self-paced certifications in responsive web, JavaScript, Python, and data.",
        "url": "https://www.freecodecamp.org/learn/",
        "source": "freeCodeCamp",
        "difficulty": "beginner",
        "tags": ["web", "javascript", "python", "html", "css"],
    },
    {
        "title": "Khan Academy: AP Computer Science Principles",
        "description": "Foundations of computing, data, internet, and programming concepts.",
        "url": "https://www.khanacademy.org/computing/ap-computer-science-principles",
        "source": "Khan Academy",
        "difficulty": "beginner",
        "tags": ["computer-science", "programming", "ap-csp"],
    },
    {
        "title": "Khan Academy: Linear Algebra",
        "description": "Vectors, matrices, transformations — useful for ML and graphics.",
        "url": "https://www.khanacademy.org/math/linear-algebra",
        "source": "Khan Academy",
        "difficulty": "intermediate",
        "tags": ["math", "linear-algebra", "vectors", "matrices"],
    },
    {
        "title": "fast.ai Practical Deep Learning for Coders",
        "description": "Hands-on deep learning with PyTorch, focused on getting models working fast.",
        "url": "https://course.fast.ai/",
        "source": "fast.ai",
        "difficulty": "intermediate",
        "tags": ["machine-learning", "deep-learning", "pytorch", "ai"],
    },
    {
        "title": "Google IT Automation with Python",
        "description": "Python scripting, Git, troubleshooting, and automation for IT roles.",
        "url": "https://www.coursera.org/professional-certificates/google-it-automation",
        "source": "Coursera / Google (free audit)",
        "difficulty": "beginner",
        "tags": ["python", "automation", "linux", "git"],
    },
    {
        "title": "Stanford CS229: Machine Learning",
        "description": "Graduate-level ML: supervised learning, generative models, reinforcement learning.",
        "url": "https://cs229.stanford.edu/",
        "source": "Stanford",
        "difficulty": "advanced",
        "tags": ["machine-learning", "math", "statistics", "ai"],
    },
]


def fetch_courses(query: str, max_results: int = 10) -> list[LearningResource]:
    """
    Return curated courses that loosely match the query.

    Step 1: Score each course by keyword overlap with the query.
    Step 2: Return the best matches (or all courses if nothing matches well).

    Semantic ranking in recommender.py does the final smart sorting.
    """
    query_words = _tokenize(query)

    scored: list[tuple[int, dict]] = []
    for course in CURATED_COURSES:
        # Search title, description, and tags for query words
        searchable = " ".join(
            [course["title"], course["description"], " ".join(course["tags"])]
        ).lower()
        score = sum(1 for word in query_words if word in searchable)
        scored.append((score, course))

    # Sort by match score (highest first)
    scored.sort(key=lambda pair: pair[0], reverse=True)

    # If nothing matched, still return courses — embeddings will rank them
    if scored[0][0] == 0:
        selected = [course for _, course in scored[:max_results]]
    else:
        # Prefer courses with at least one keyword hit
        selected = [course for score, course in scored if score > 0][:max_results]
        if not selected:
            selected = [course for _, course in scored[:max_results]]

    return [
        LearningResource(
            title=c["title"],
            description=c["description"],
            url=c["url"],
            source=c["source"],
            difficulty=c["difficulty"],
            tags=c["tags"],
            resource_type="course",
        )
        for c in selected
    ]


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase words for simple keyword matching."""
    stopwords = {"the", "and", "for", "with", "how", "what", "learn", "about"}
    return [
        word.strip("?.!,")
        for word in text.lower().split()
        if len(word) > 2 and word not in stopwords
    ]
