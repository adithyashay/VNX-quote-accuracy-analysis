import json

from psycopg2.extras import Json

from src.database.connection import get_connection
from src.market_hours import get_current_eastern_time


CREATE_PIPELINE_HEALTH_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_health_events (
    id SERIAL PRIMARY KEY,
    component TEXT NOT NULL,
    status TEXT NOT NULL,
    event_time TIMESTAMP NOT NULL,
    message TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_PIPELINE_HEALTH_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_pipeline_health_component_time
    ON pipeline_health_events (component, event_time DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_health_status_time
    ON pipeline_health_events (status, event_time DESC);
"""


def create_pipeline_health_table():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PIPELINE_HEALTH_EVENTS_TABLE)
            cursor.execute(CREATE_PIPELINE_HEALTH_EVENTS_INDEXES)

        connection.commit()


def record_pipeline_event(
    component,
    status,
    message=None,
    details=None,
    event_time=None,
):
    if not component:
        raise ValueError("component is required")

    if not status:
        raise ValueError("status is required")

    if details is None:
        details = {}

    if event_time is None:
        event_time = get_current_eastern_time().replace(tzinfo=None)

    query = """
        INSERT INTO pipeline_health_events (
            component,
            status,
            event_time,
            message,
            details
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_PIPELINE_HEALTH_EVENTS_TABLE)
            cursor.execute(CREATE_PIPELINE_HEALTH_EVENTS_INDEXES)
            cursor.execute(
                query,
                (
                    component,
                    status,
                    event_time,
                    message,
                    Json(details, dumps=lambda value: json.dumps(value, default=str)),
                ),
            )

        connection.commit()
