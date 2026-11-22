-- The app creates this table itself at startup while DB_BOOTSTRAP_ON_STARTUP=true.
-- Keep this file for databases where bootstrap is off (e.g. production).
-- Why a new table: the ERD's audit_logs requires org_id and action and has no request
-- metadata columns. The gateway AuditLog model needs a different shape.

CREATE TABLE IF NOT EXISTS gateway_audit_logs (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id         uuid NOT NULL,
  requested_mode     varchar(32),
  enforced_mode      varchar(32),
  auto_rerouted      boolean NOT NULL DEFAULT false,
  threat_category    varchar(64),
  model_used         varchar(128),
  provider_used      varchar(64),
  faithfulness_score double precision,
  latency_ms         double precision,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_gateway_audit_logs_request_id ON gateway_audit_logs (request_id);
