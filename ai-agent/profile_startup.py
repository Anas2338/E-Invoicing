"""Profile AI Agent startup time to identify bottlenecks."""
import time
import sys
from pathlib import Path

def profile_step(name, func):
    """Time a function and print result."""
    start = time.time()
    result = func()
    elapsed = (time.time() - start) * 1000
    print(f"{name:.<50} {elapsed:>6.0f}ms")
    return result

print("=" * 60)
print("AI AGENT STARTUP PROFILING")
print("=" * 60)

total_start = time.time()

# Step 1: Load environment
def step1():
    from dotenv import load_dotenv
    load_dotenv()
profile_step("1. Load .env file", step1)

# Step 2: Setup paths
def step2():
    project_root = Path(__file__).parent.parent
    backend_path = project_root / "backend"
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(backend_path))
profile_step("2. Setup import paths", step2)

# Step 3: Import SQLAlchemy models
def step3():
    from src.models.user import User
    from src.models.excel_upload_session import ExcelUploadSession
    from src.models.automation_invoice import AutomationInvoice
    from src.models.automation_log import AutomationLog
    from src.models.ai_agent_health_check import AIAgentHealthCheck
profile_step("3. Import SQLAlchemy models", step3)

# Step 4: Import config
def step4():
    from config import config
    return config
config = profile_step("4. Load configuration", step4)

# Step 5: Import database (creates connection pool)
def step5():
    from database import get_db_session, engine
profile_step("5. Initialize database pool", step5)

# Step 6: Import validation
def step6():
    from validation import validate_environment
profile_step("6. Import validation module", step6)

# Step 7: Import skills
def step7():
    from skills.priority_scheduler import PrioritySchedulerSkill
    from skills.invoice_validator import InvoiceValidatorSkill
    from skills.fbr_poster import FBRPosterSkill
    from skills.error_handler import ErrorHandlerSkill
    from skills.retry_manager import RetryManagerSkill
profile_step("7. Import all skills", step7)

# Step 8: Import agent
def step8():
    from agent import AIAgent
profile_step("8. Import AIAgent class", step8)

# Step 9: Run validation
def step9():
    from validation import validate_environment
    validate_environment()
profile_step("9. Run environment validation", step9)

total_elapsed = (time.time() - total_start) * 1000
print("=" * 60)
print(f"TOTAL STARTUP TIME: {total_elapsed:.0f}ms ({total_elapsed/1000:.1f}s)")
print("=" * 60)
