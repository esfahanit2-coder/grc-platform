import json
from django.utils import timezone
from apps.evidence.models import Evidence
from apps.audit.services import record_audit_event
from .clients import connector_for
from .models import ConnectorRun

def run_connector(config, *, user, request=None):
    run=ConnectorRun.objects.create(connector=config,triggered_by=user,status=ConnectorRun.Status.RUNNING)
    try:
        result=connector_for(config).collect()
        evidence=Evidence.objects.create(tenant=config.tenant,organization_unit=config.organization_unit,title=result.title,description=f"Automated evidence from connector {config.name}",evidence_type=Evidence.EvidenceType.CONFIGURATION,source=f"connector:{config.connector_type}:{config.id}",owner=user,collected_at=timezone.now(),classification=Evidence.Classification.INTERNAL,text_content=json.dumps(result.payload,ensure_ascii=False,default=str),metadata={"connector_id":str(config.id),"connector_type":config.connector_type,"automated":True})
        run.status=ConnectorRun.Status.SUCCEEDED;run.finished_at=timezone.now();run.summary={"evidence_id":str(evidence.id),"title":result.title};run.save(update_fields=["status","finished_at","summary","updated_at"])
        config.last_sync_at=run.finished_at;config.last_status="succeeded";config.last_error="";config.save(update_fields=["last_sync_at","last_status","last_error","updated_at"])
        record_audit_event(user,config.tenant,"connector.run","connector_config",config.id,metadata={"connector_type":config.connector_type,"evidence_id":str(evidence.id)},request=request)
        return run,evidence
    except Exception as exc:
        run.status=ConnectorRun.Status.FAILED;run.finished_at=timezone.now();run.error=str(exc)[:4000];run.save(update_fields=["status","finished_at","error","updated_at"])
        config.last_sync_at=run.finished_at;config.last_status="failed";config.last_error=run.error;config.save(update_fields=["last_sync_at","last_status","last_error","updated_at"])
        record_audit_event(user,config.tenant,"connector.run","connector_config",config.id,outcome="failure",metadata={"connector_type":config.connector_type,"error":run.error},request=request)
        raise
