import base64
import json
import os
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from django.conf import settings
from rest_framework.exceptions import ValidationError
from .models import ConnectorConfig

@dataclass
class ConnectorResult:
    title: str
    payload: dict

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValidationError(f"Connector redirects are disabled (HTTP {code}).")

class BaseConnector:
    def __init__(self, config): self.config=config
    def _secret(self,name): return os.getenv(name,"") if name else ""
    def collect(self): raise NotImplementedError
    def health(self): self.collect(); return {"ok":True}
    def _json(self, path, *, headers=None, method="GET", data=None):
        base=self.config.base_url.rstrip("/")
        parsed=urllib.parse.urlparse(base)
        if parsed.scheme not in {"https","http"} or not parsed.hostname:
            raise ValidationError("Connector base_url must be an http(s) URL with a hostname.")
        if parsed.scheme != "https" and getattr(settings,"APP_ENV","development") == "production":
            raise ValidationError("Production HTTP connectors must use HTTPS.")
        url=base+path
        req=urllib.request.Request(url,data=data,headers=headers or {},method=method)
        context=ssl.create_default_context() if self.config.verify_tls else ssl._create_unverified_context()
        if not self.config.verify_tls and getattr(settings,"APP_ENV","development") == "production":
            raise ValidationError("TLS verification cannot be disabled for production HTTP connectors.")
        max_bytes=int(getattr(settings,"CONNECTOR_MAX_RESPONSE_BYTES",5*1024*1024))
        opener=urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context), urllib.request.HTTPHandler())
        try:
            with opener.open(req,timeout=getattr(settings,"CONNECTOR_HTTP_TIMEOUT",30)) as response:
                raw_bytes=response.read(max_bytes+1)
                if len(raw_bytes)>max_bytes:
                    raise ValidationError("Connector response exceeded the configured size limit.")
                raw=raw_bytes.decode("utf-8",errors="replace")
                return json.loads(raw) if raw.strip() else {}, response.headers
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(f"Connector request failed: {exc}") from exc

class FortiGateConnector(BaseConnector):
    def collect(self):
        token=self._secret(self.config.secret_env_var)
        if not token: raise ValidationError("FortiGate API token secret is missing.")
        headers={"Accept":"application/json","Authorization":f"Bearer {token}"}
        paths=(self.config.configuration or {}).get("read_paths") or ["/api/v2/cmdb/system/global"]
        if len(paths)>10: raise ValidationError("At most 10 FortiGate read paths are allowed per run.")
        results={}
        for path in paths:
            if not str(path).startswith("/api/v2/"): raise ValidationError("FortiGate connector permits only /api/v2/ read paths.")
            data,_=self._json(path,headers=headers);results[path]=data
        return ConnectorResult("FortiGate configuration snapshot",{"paths":results})

class TenableConnector(BaseConnector):
    def collect(self):
        access=self._secret(self.config.username_env_var); secret=self._secret(self.config.secret_env_var)
        if not access or not secret: raise ValidationError("Tenable access/secret key environment variables are required.")
        headers={"Accept":"application/json","X-ApiKeys":f"accessKey={access}; secretKey={secret}"}
        data,_=self._json("/scans",headers=headers)
        scans=data.get("scans") or []
        summary=[{"id":row.get("id"),"name":row.get("name"),"status":row.get("status"),"last_modification_date":row.get("last_modification_date")} for row in scans[:200]]
        return ConnectorResult("Tenable scan inventory",{"scan_count":len(scans),"scans":summary})

class VeeamConnector(BaseConnector):
    def _session(self):
        username=self._secret(self.config.username_env_var); password=self._secret(self.config.secret_env_var)
        if not username or not password: raise ValidationError("Veeam username/password environment variables are required.")
        auth=base64.b64encode(f"{username}:{password}".encode()).decode()
        _,headers=self._json("/api/sessionMngr/?v=latest",headers={"Authorization":f"Basic {auth}","Accept":"application/json"},method="POST",data=b"")
        token=headers.get("X-RestSvcSessionId")
        if not token: raise ValidationError("Veeam did not return X-RestSvcSessionId.")
        return token
    def collect(self):
        token=self._session(); headers={"Accept":"application/json","X-RestSvcSessionId":token}
        backups,_=self._json("/api/backups",headers=headers)
        sessions,_=self._json("/api/backupSessions",headers=headers)
        return ConnectorResult("Veeam backup assurance snapshot",{"backups":backups,"backup_sessions":sessions})

class ActiveDirectoryConnector(BaseConnector):
    def collect(self):
        try:
            from ldap3 import ALL, Connection, Server, SUBTREE
        except ImportError as exc:
            raise ValidationError("ldap3 package is required for the Active Directory connector.") from exc
        username=self._secret(self.config.username_env_var); password=self._secret(self.config.secret_env_var)
        cfg=self.config.configuration or {}; host=cfg.get("host") or self.config.base_url; base_dn=cfg.get("base_dn")
        if isinstance(host,str) and "://" in host: host=urllib.parse.urlparse(host).hostname or host
        if not host or not base_dn: raise ValidationError("AD connector requires host/base_dn configuration.")
        server=Server(host,use_ssl=bool(cfg.get("use_ssl",True)),get_info=ALL,connect_timeout=getattr(settings,"CONNECTOR_HTTP_TIMEOUT",30))
        conn=Connection(server,user=username or None,password=password or None,auto_bind=True,receive_timeout=getattr(settings,"CONNECTOR_HTTP_TIMEOUT",30))
        search_filter=cfg.get("search_filter") or "(&(objectCategory=person)(objectClass=user))"
        attributes=cfg.get("attributes") or ["distinguishedName","sAMAccountName","userAccountControl","whenChanged"]
        conn.search(base_dn,search_filter,search_scope=SUBTREE,attributes=attributes,size_limit=int(cfg.get("size_limit",5000)))
        rows=[]
        disabled=0
        for entry in conn.entries:
            record={attr:str(entry[attr]) for attr in attributes if attr in entry}
            try:
                uac=int(str(entry["userAccountControl"])) if "userAccountControl" in entry else 0
                if uac & 2: disabled+=1
            except Exception: pass
            rows.append(record)
        conn.unbind()
        return ConnectorResult("Active Directory account inventory",{"user_count":len(rows),"disabled_count":disabled,"sample":rows[:100]})

def connector_for(config):
    mapping={
        ConnectorConfig.ConnectorType.FORTIGATE:FortiGateConnector,
        ConnectorConfig.ConnectorType.TENABLE:TenableConnector,
        ConnectorConfig.ConnectorType.VEEAM:VeeamConnector,
        ConnectorConfig.ConnectorType.ACTIVE_DIRECTORY:ActiveDirectoryConnector,
    }
    cls=mapping.get(config.connector_type)
    if not cls: raise ValidationError("Unsupported connector type.")
    return cls(config)
