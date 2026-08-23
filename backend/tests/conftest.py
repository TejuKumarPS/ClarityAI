import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.base import Base
from app.core.database import get_db

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/clarityai_test",
)

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


from app.worker import tasks as worker_tasks
from app.core.database import SessionLocal as DevSessionLocal

@pytest.fixture(autouse=True)
def configure_worker_test_db():
    worker_tasks.SessionLocal = TestingSessionLocal
    yield
    worker_tasks.SessionLocal = DevSessionLocal



@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.core.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def mock_celery_delay_if_no_redis(monkeypatch, request):
    # Skip mocking for tests that specifically test Redis or enqueue failures
    skip_tests = {
        "test_redis_connectivity",
        "test_celery_broker_connection",
        "test_job_creation_enqueue_failure_handling",
    }
    if request.node.name in skip_tests:
        yield
        return

    import redis
    from app.core.config import settings
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=0.5)
        r.ping()
    except Exception:
        from app.worker import tasks as worker_tasks
        monkeypatch.setattr(worker_tasks.process_job, "delay", lambda *args, **kwargs: None)
    yield
