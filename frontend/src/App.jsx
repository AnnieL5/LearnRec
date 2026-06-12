import { useState } from "react";
import { fetchRecommendations } from "./api";
import RecommendationCard from "./RecommendationCard";
import "./App.css";

const EXAMPLE_PROFILE =
  "I know basic Python and want fast hands-on AI projects.";

function App() {
  const [profile, setProfile] = useState(EXAMPLE_PROFILE);
  const [recommendations, setRecommendations] = useState([]);
  const [parsedProfile, setParsedProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    setRecommendations([]);
    setParsedProfile(null);

    try {
      const data = await fetchRecommendations(profile.trim());
      setRecommendations(data.recommendations);
      setParsedProfile(data.profile);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header accent-block accent-block--blue">
        <div className="accent-bar" aria-hidden="true" />
        <div className="accent-content">
          <h1>Learn Rec</h1>
          <p className="subtitle">
            Your personalized study resource recommender.
          </p>
        </div>
      </header>

      <main className="main">
        <form className="form" onSubmit={handleSubmit}>
          <div className="accent-block accent-block--green profile-section">
            <div className="accent-bar" aria-hidden="true" />
            <div className="accent-content">
              <label className="form-label" htmlFor="profile">
              Describe your goals, experience, and learning style in plain English
              </label>
              <textarea
                id="profile"
                className="textarea"
                rows={5}
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                placeholder="e.g. I am new to Python and want hands-on AI projects."
                disabled={loading}
                minLength={10}
                required
              />
            </div>
          </div>
          <button className="submit-btn" type="submit" disabled={loading}>
            {loading ? "Finding resources…" : "Get recommendations"}
          </button>
        </form>

        {loading && (
          <div className="loading" role="status" aria-live="polite">
            <div className="spinner" />
            <p>Searching videos, courses, and articles…</p>
          </div>
        )}

        {error && <p className="error">{error}</p>}

        {parsedProfile && !loading && (
          <section className="parsed-profile">
            <div className="accent-block accent-block--blue section-heading">
              <div className="accent-bar" aria-hidden="true" />
              <h2>Based on:</h2>
            </div>
            <ul>
              <li>
                <strong>Level:</strong> {parsedProfile.experience_level}
              </li>
              <li>
                <strong>Style:</strong>{" "}
                {parsedProfile.learning_styles.length > 0
                  ? parsedProfile.learning_styles.join(", ")
                  : "flexible"}
              </li>
              <li>
                <strong>Interests:</strong>{" "}
                {parsedProfile.interests.length > 0
                  ? parsedProfile.interests.join(", ")
                  : "general"}
              </li>
            </ul>
          </section>
        )}

        {recommendations.length > 0 && !loading && (
          <section className="results">
            <div className="accent-block accent-block--blue section-heading">
              <div className="accent-bar" aria-hidden="true" />
              <h2>Top recommendations</h2>
            </div>
            <div className="card-list">
              {recommendations.map((rec, index) => (
                <RecommendationCard
                  key={`${rec.url}-${index}`}
                  recommendation={rec}
                  index={index}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
