-- Migration: structured job requirements. A job can name the skills it needs;
-- matching then uses them exactly instead of guessing from the text.
-- Additive and re-runnable. `activation` only.
CREATE TABLE IF NOT EXISTS activation.opportunity_requirements (
    opportunity_id uuid NOT NULL REFERENCES activation.opportunities(id) ON DELETE CASCADE,
    capability_id  uuid NOT NULL REFERENCES activation.capabilities(id) ON DELETE CASCADE,
    PRIMARY KEY (opportunity_id, capability_id)
);

CREATE INDEX IF NOT EXISTS idx_opp_requirements_capability
    ON activation.opportunity_requirements (capability_id);

ALTER TABLE activation.opportunity_requirements ENABLE ROW LEVEL SECURITY;
