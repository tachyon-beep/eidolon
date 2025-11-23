"""
Review Loop System for Agent Negotiation

Implements multi-level review where:
1. A primary agent (DESIGN, IMPLEMENTATION) generates output
2. A REVIEW agent critiques the output
3. If quality is insufficient, primary agent revises based on feedback
4. Process repeats until quality threshold met or max iterations reached

This enables agent negotiation and self-correction at each tier.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json

from llm_providers import LLMProvider
from planning.agent_selector import AgentRole
from planning.prompt_templates import PromptTemplateLibrary
from planning.improved_decomposition import extract_json_from_response
from logging_config import get_logger

logger = get_logger(__name__)


class ReviewDecision(str, Enum):
    """Review agent's decision"""
    ACCEPT = "accept"           # Output meets quality standards
    REVISE_MINOR = "revise_minor"  # Small issues, needs minor revision
    REVISE_MAJOR = "revise_major"  # Significant issues, needs major revision
    REJECT = "reject"           # Critical issues, fundamentally flawed


@dataclass
class ReviewResult:
    """Result of a review"""
    decision: ReviewDecision
    score: float  # 0-100
    strengths: List[str]
    issues: List[str]
    suggestions: List[str]
    reasoning: str


class ReviewLoop:
    """
    Manages review-and-revise cycles for agent outputs

    Usage:
        loop = ReviewLoop(llm_provider)
        result = await loop.review_and_revise(
            initial_output=plan,
            primary_agent_func=design_agent.decompose,
            review_context={"tier": "system", "type": "subsystem_decomposition"},
            min_score=80,
            max_iterations=3
        )
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def review_and_revise(
        self,
        initial_output: Dict[str, Any],
        primary_agent_func: Callable,
        review_context: Dict[str, Any],
        min_score: float = 75.0,
        max_iterations: int = 3,
        skip_review: bool = False
    ) -> Dict[str, Any]:
        """
        Execute review-and-revise loop

        Args:
            initial_output: First attempt from primary agent
            primary_agent_func: Function to call for revisions (async callable)
            review_context: Context for review (tier, type, original request, etc.)
            min_score: Minimum acceptable quality score (0-100)
            max_iterations: Maximum revision attempts
            skip_review: If True, skip review loop (for testing/fallback)

        Returns:
            Final output after review/revision cycles
        """
        if skip_review:
            logger.info("review_skipped", reason="skip_review=True")
            return initial_output

        current_output = initial_output
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Review current output
            review = await self._review_output(current_output, review_context)

            logger.info(
                "review_iteration",
                iteration=iteration,
                decision=review.decision.value,
                score=review.score,
                issues_count=len(review.issues)
            )

            # Check if output is acceptable
            if review.decision == ReviewDecision.ACCEPT or review.score >= min_score:
                logger.info(
                    "review_accepted",
                    iteration=iteration,
                    score=review.score,
                    total_iterations=iteration
                )
                return self._add_review_metadata(current_output, review, iteration)

            # Check if output is fundamentally flawed
            if review.decision == ReviewDecision.REJECT:
                logger.error(
                    "review_rejected",
                    iteration=iteration,
                    score=review.score,
                    issues=review.issues
                )
                # Return output with failure metadata
                return self._add_review_metadata(
                    current_output,
                    review,
                    iteration,
                    failed=True
                )

            # Check if we've hit max iterations
            if iteration >= max_iterations:
                logger.warning(
                    "review_max_iterations",
                    score=review.score,
                    max_iterations=max_iterations
                )
                return self._add_review_metadata(
                    current_output,
                    review,
                    iteration,
                    max_iterations_reached=True
                )

            # Revise output based on feedback
            try:
                current_output = await self._revise_output(
                    current_output,
                    review,
                    primary_agent_func,
                    review_context
                )
            except Exception as e:
                logger.error(
                    "revision_failed",
                    error=str(e),
                    iteration=iteration
                )
                # Return current output with error metadata
                return self._add_review_metadata(
                    current_output,
                    review,
                    iteration,
                    revision_error=str(e)
                )

        # Should not reach here, but return current output if we do
        return current_output

    async def _review_output(
        self,
        output: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ReviewResult:
        """
        Have REVIEW agent critique the output

        Args:
            output: Output to review (plan, code, etc.)
            context: Context for review (tier, type, original request)

        Returns:
            ReviewResult with decision, score, issues, suggestions
        """
        # Build review prompt based on tier/type
        tier = context.get("tier", "unknown")
        output_type = context.get("type", "unknown")
        original_request = context.get("original_request", "")

        # Format output for review
        output_str = self._format_output_for_review(output, output_type)

        system_prompt = f"""You are a senior code reviewer and architect evaluating {output_type} outputs.

Your task:
1. Analyze the output for correctness, completeness, and quality
2. Identify strengths and weaknesses
3. Provide specific, actionable feedback
4. Assign a quality score (0-100)
5. Make a decision: ACCEPT, REVISE_MINOR, REVISE_MAJOR, or REJECT

Evaluation criteria:
- Correctness: Does it correctly address the request?
- Completeness: Are all required elements present?
- Specificity: Are instructions detailed and actionable?
- Best Practices: Does it follow software engineering best practices?
- Dependencies: Are dependencies properly identified?
- Clarity: Is the output clear and unambiguous?"""

        user_prompt = f"""# Review Request

**Tier**: {tier}
**Type**: {output_type}
**Original Request**: {original_request}

**Output to Review**:
```json
{output_str}
```

Provide a thorough review in JSON format:
{{
  "decision": "accept|revise_minor|revise_major|reject",
  "score": 85.5,
  "strengths": ["Strength 1", "Strength 2", ...],
  "issues": ["Issue 1", "Issue 2", ...],
  "suggestions": ["Suggestion 1", "Suggestion 2", ...],
  "reasoning": "Brief explanation of the decision"
}}

**Decision Guidelines**:
- ACCEPT (score ≥ 80): Output is production-ready
- REVISE_MINOR (score 60-79): Minor issues, mostly acceptable
- REVISE_MAJOR (score 40-59): Significant issues, needs substantial revision
- REJECT (score < 40): Fundamentally flawed, cannot be salvaged with minor revisions"""

        try:
            # Call LLM with review prompts
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2048,
                temperature=0.0
            )

            # Parse review response
            review_data = extract_json_from_response(response.content)

            if not review_data:
                raise ValueError("Failed to parse review response as JSON")

            # Create ReviewResult
            # Convert decision to lowercase for case-insensitive enum lookup
            decision_str = review_data.get("decision", "revise_major")
            if isinstance(decision_str, str):
                decision_str = decision_str.lower()

            return ReviewResult(
                decision=ReviewDecision(decision_str),
                score=float(review_data.get("score", 50.0)),
                strengths=review_data.get("strengths", []),
                issues=review_data.get("issues", []),
                suggestions=review_data.get("suggestions", []),
                reasoning=review_data.get("reasoning", "")
            )

        except Exception as e:
            logger.error("review_parsing_failed", error=str(e))
            # Return a default "revise" review on error
            return ReviewResult(
                decision=ReviewDecision.REVISE_MINOR,
                score=60.0,
                strengths=[],
                issues=[f"Review parsing failed: {str(e)}"],
                suggestions=["Proceed with caution, review was inconclusive"],
                reasoning="Failed to parse review, defaulting to REVISE_MINOR"
            )

    async def _revise_output(
        self,
        current_output: Dict[str, Any],
        review: ReviewResult,
        primary_agent_func: Callable,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Have primary agent revise output based on review feedback

        Args:
            current_output: Current version of output
            review: Review results with feedback
            primary_agent_func: Function to regenerate output
            context: Context for revision

        Returns:
            Revised output
        """
        # Build revision prompt with feedback
        feedback_str = self._format_feedback(review)

        # Add feedback to context
        revision_context = {
            **context,
            "revision_feedback": feedback_str,
            "previous_output": current_output,
            "is_revision": True
        }

        # Call primary agent function with revision context
        # Note: This assumes primary_agent_func accepts context parameter
        # In practice, we may need to adapt based on the specific function signature
        revised_output = await primary_agent_func(**revision_context)

        return revised_output

    def _format_output_for_review(self, output: Dict[str, Any], output_type: str) -> str:
        """Format output for review (convert to readable JSON string)"""
        import json
        try:
            return json.dumps(output, indent=2)
        except:
            return str(output)

    def _format_feedback(self, review: ReviewResult) -> str:
        """Format review feedback for revision prompt"""
        feedback_parts = []

        feedback_parts.append(f"**Review Score**: {review.score}/100")
        feedback_parts.append(f"**Decision**: {review.decision.value}")

        if review.strengths:
            feedback_parts.append("\n**Strengths**:")
            for strength in review.strengths:
                feedback_parts.append(f"  ✅ {strength}")

        if review.issues:
            feedback_parts.append("\n**Issues to Address**:")
            for issue in review.issues:
                feedback_parts.append(f"  ❌ {issue}")

        if review.suggestions:
            feedback_parts.append("\n**Suggestions for Improvement**:")
            for suggestion in review.suggestions:
                feedback_parts.append(f"  💡 {suggestion}")

        if review.reasoning:
            feedback_parts.append(f"\n**Reasoning**: {review.reasoning}")

        return "\n".join(feedback_parts)

    def _add_review_metadata(
        self,
        output: Dict[str, Any],
        review: ReviewResult,
        iterations: int,
        failed: bool = False,
        max_iterations_reached: bool = False,
        revision_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add review metadata to output"""
        output["_review_metadata"] = {
            "iterations": iterations,
            "final_score": review.score,
            "final_decision": review.decision.value,
            "failed": failed,
            "max_iterations_reached": max_iterations_reached,
            "revision_error": revision_error,
            "strengths": review.strengths,
            "issues": review.issues,
            "suggestions": review.suggestions
        }
        return output


# Helper function for quick review
async def quick_review(
    llm_provider: LLMProvider,
    output: Dict[str, Any],
    context: Dict[str, Any],
    min_score: float = 75.0
) -> ReviewResult:
    """
    Perform a single review without revision loop

    Useful for testing or final quality checks
    """
    loop = ReviewLoop(llm_provider)
    return await loop._review_output(output, context)
