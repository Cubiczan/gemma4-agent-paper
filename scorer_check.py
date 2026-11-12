"""Replicates the scorer's pre-run + per-task compile path with the released swegemma 0.2.7 / adk_submission 0.2.11."""
import sys,os,zipfile,tempfile; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','official_harness_ref')); os.environ['LITELLM_LOCAL_MODEL_COST_MAP']='True'
from swegemma.context import SwegemmaContext
from swegemma.config import build_submission_limits, ALLOWED_SUBMISSION_EXTENSIONS
from swegemma.models.registry import setup_gemma_model_registry, resolve_swegemma_adapter
from swegemma.models.discovery import validate_single_declared_model
from adk_submission import compile_submission, discover_adapters, ToolRegistry
import swegemma.harness.agent_runner as ar
for z in sys.argv[1:]:
    d=tempfile.mkdtemp(); zipfile.ZipFile(z).extractall(d)
    bad=[n for n in zipfile.ZipFile(z).namelist() if not n.endswith('/') and os.path.splitext(n)[1].lower() not in ALLOWED_SUBMISSION_EXTENSIONS]
    m=validate_single_declared_model(d); ad=discover_adapters(d)
    ctx=SwegemmaContext(problem_statement='x',task_id='t',repo='r'); tr=ToolRegistry()
    for k,v in ctx.create_tools().items(): tr.register(k,v)
    models=setup_gemma_model_registry(api_base='http://127.0.0.1:8000/v1', served_model=m)
    lim,gc=build_submission_limits()
    ex=ar.AdkSandboxCodeExecutor(sandbox=ctx.sandbox,timeout_seconds=180,start_time=ctx.task_start_time,max_time_minutes=4.5,budget_check_fn=ctx.check_budget)
    a=compile_submission(submission_dir=d,tool_registry=tr,model_registry=models,code_executor=ex,script_timeout=180,limits=lim,generation_constraints=gc,adapter_manifest=ad,adapter_resolver_fn=lambda b,i: resolve_swegemma_adapter(b,i,models))
    print(z,'OK model=',m,'adapters=',list(ad.adapters),'bad_ext=',bad,'tools=',len(a.tools),'thinking=',a.model._additional_args.get('extra_body'))
