CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS audit;

COMMENT ON SCHEMA source IS 'Synthetic operational source tables';
COMMENT ON SCHEMA serving IS 'Rebuildable Member 360 serving projections';
COMMENT ON SCHEMA audit IS 'Pipeline, publish, and access audit records';

