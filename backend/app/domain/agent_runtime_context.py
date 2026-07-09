from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AgentRuntimeContext(BaseModel):
    """Runtime context passed to the agent per request.

    Describes the current analysis date and the bounds of available sales data.
    Used to resolve relative date phrases (e.g. 'this year', 'last month') into
    concrete ISO date ranges before the agent calls any data tool.

    Values are provided by get_agent_runtime_context() in
    app/adapters/inbound/api/dependencies.py.  Replace that function body with a
    real MCP/database/config lookup when data availability becomes dynamic.
    """

    current_date: date
    available_data_from: date
    available_data_to: date
