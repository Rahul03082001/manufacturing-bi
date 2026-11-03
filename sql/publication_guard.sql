-- Owner-installed backstop: runtime cannot point reporting at a rejected/incomplete run.
CREATE OR REPLACE FUNCTION reporting.require_approved_run() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM audit.outcomes WHERE run_id=NEW.run_id AND outcome='SUCCESS')
 OR (SELECT count(*) FROM audit.checks WHERE run_id=NEW.run_id AND passed
     AND control IN ('source_delivery','schema_validity','business_key_uniqueness','relationships',
                     'business_rules','receipt_quantities','negative_inventory','reconciliation')) <> 8
 OR EXISTS (SELECT 1 FROM audit.checks WHERE run_id=NEW.run_id AND NOT passed) THEN
   RAISE EXCEPTION 'Publication requires a successful run and all eight critical controls' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER require_approved_run BEFORE INSERT OR UPDATE ON reporting.publication
FOR EACH ROW EXECUTE FUNCTION reporting.require_approved_run();
