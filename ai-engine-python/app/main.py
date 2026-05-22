"""
ai-engine-python service entry (architecture scaffold).

Role in system:
- internal-only compute service, not exposed to public frontend
- receives requests from gateway-rust
- executes heavy compute: planning, tutor inference, graph updates
"""

# NOTE:
# FastAPI app/router wiring is intentionally not implemented yet.
# Keep this module as a placeholder until service contract is finalized.


def bootstrap_placeholder() -> None:
    """
    Placeholder startup hook.

    Future responsibilities:
    1) load model/runtime configs
    2) initialize OR-Tools environment
    3) initialize Redis + Neo4j clients
    4) register internal API endpoints
    """

    # Intentionally no runtime logic in architecture phase.
    return None
