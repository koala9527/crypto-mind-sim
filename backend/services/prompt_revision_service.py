"""提示词版本历史记录服务。"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.models import PromptConfig, PromptRevisionHistory


def record_prompt_revision(
    db: Session,
    strategy: PromptConfig,
    source: str,
    summary: str,
    prompt_text: str,
    previous_prompt_text: str | None = None,
    base_prompt_text: str | None = None,
) -> PromptRevisionHistory:
    last_revision_no = (
        db.query(func.max(PromptRevisionHistory.revision_no))
        .filter(PromptRevisionHistory.strategy_id == strategy.id)
        .scalar()
        or 0
    )

    revision = PromptRevisionHistory(
        strategy_id=strategy.id,
        user_id=strategy.user_id,
        revision_no=last_revision_no + 1,
        source=source,
        summary=summary,
        previous_prompt_text=previous_prompt_text,
        prompt_text=prompt_text,
        base_prompt_text=base_prompt_text,
    )
    db.add(revision)
    return revision
