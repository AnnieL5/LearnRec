/**
 * api.js
 * ------
 * Talks to the FastAPI backend.
 *
 * During development, Vite proxies /api → http://localhost:8000
 * (see vite.config.js). Start the backend with:
 *   uvicorn main:app --reload
 */

const API_BASE = "/api";

/**
 * Send a learner profile and get ranked recommendations.
 *
 * @param {string} profile - Natural-language description of goals and preferences
 * @param {number} topK - How many results to return (default 5)
 * @returns {Promise<object>} Full API response with profile + recommendations
 */
export async function fetchRecommendations(profile, topK = 5) {
  const response = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, top_k: topK }),
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message = typeof errorBody.detail === "string"
          ? errorBody.detail
          : JSON.stringify(errorBody.detail);
      }
    } catch {
      // use default message
    }
    throw new Error(message);
  }

  return response.json();
}

/**
 * Build a short human-readable explanation from score breakdown.
 * The API returns numbers; this turns them into plain English for the UI.
 */
export function buildExplanation(recommendation) {
  const { score_breakdown: scores, difficulty, resource_type, final_score } =
    recommendation;

  const parts = [];

  parts.push(`Overall match: ${Math.round(final_score * 100)}%.`);

  if (scores.topic >= 0.5) {
    parts.push("Strong topic overlap with your interests.");
  } else if (scores.semantic >= 0.4) {
    parts.push("Semantically similar to what you described.");
  }

  if (scores.difficulty >= 0.7) {
    parts.push(`Good fit for ${difficulty} level content.`);
  }

  if (scores.learning_style >= 0.7) {
    parts.push("Aligns with your preferred learning style.");
  }

  parts.push(`Resource type: ${resource_type}.`);

  return parts.join(" ");
}
