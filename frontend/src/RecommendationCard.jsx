import { buildExplanation } from "./api";

/**
 * RecommendationCard
 * ------------------
 * Displays one recommended learning resource.
 */
function RecommendationCard({ recommendation, index }) {
  const explanation = buildExplanation(recommendation);

  return (
    <article className="card">
      <div className="card-header">
        <span className="card-rank">#{index + 1}</span>
        <span className="card-type">{recommendation.resource_type}</span>
      </div>

      <h3 className="card-title">{recommendation.title}</h3>

      <p className="card-description">{recommendation.description}</p>

      <p className="card-source">
        <span className="label">Source</span> {recommendation.source}
      </p>

      <p className="card-explanation">
        <span className="label">Why this match</span> {explanation}
      </p>

      <a
        className="card-link"
        href={recommendation.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open resource →
      </a>
    </article>
  );
}

export default RecommendationCard;
