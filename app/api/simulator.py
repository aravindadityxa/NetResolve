"""Simulator control endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.core.logging import logger
from app.simulator.simulator import get_simulator
from app.simulator.scenarios import SCENARIOS

router = APIRouter(tags=["Simulator"])


@router.get("/simulator/status")
async def get_simulator_status():
    """Get simulator status."""
    try:
        simulator = get_simulator()
        return {
            "enabled": True,
            "event_count": simulator.event_count,
            "topology_summary": simulator.get_topology_summary(),
        }
    except Exception as e:
        logger.error(f"Error getting simulator status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulator/scenarios", response_model=List[Dict[str, Any]])
async def list_scenarios():
    """List available scenarios."""
    try:
        return [
            {
                "id": name,
                "name": name.replace("_", " ").title(),
                "description": scenario.get("description", ""),
                "expected_alarms": scenario.get("expected_alarms", 0),
                "expected_root_causes": scenario.get("expected_root_causes", 0),
            }
            for name, scenario in SCENARIOS.items()
        ]
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulator/scenarios/{scenario_name}")
async def run_scenario(scenario_name: str):
    """Run a simulator scenario."""
    try:
        if scenario_name not in SCENARIOS:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario '{scenario_name}' not found. Available scenarios: {list(SCENARIOS.keys())}",
            )

        simulator = get_simulator()
        scenario_def = SCENARIOS[scenario_name]

        # Run scenario
        events = simulator.run_scenario(scenario_name)

        logger.info(f"Executed scenario '{scenario_name}': {len(events)} events generated")

        return {
            "scenario": scenario_name,
            "event_count": len(events),
            "events": [
                {
                    "id": e["id"],
                    "timestamp": e["timestamp"],
                    "event_type": e["event_type"],
                    "device_id": e["device_id"],
                    "severity": e["severity"],
                    "message": e["message"],
                }
                for e in events
            ],
            "expected_alarms": scenario_def.get("expected_alarms", 0),
            "expected_root_causes": scenario_def.get("expected_root_causes", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulator/history")
async def get_event_history(limit: int = 100):
    """Get event history."""
    try:
        simulator = get_simulator()
        events = simulator.get_event_history(limit)

        return {
            "total_events": simulator.event_count,
            "returned": len(events),
            "events": events,
        }
    except Exception as e:
        logger.error(f"Error getting event history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/simulator/history")
async def clear_event_history():
    """Clear simulator event history."""
    try:
        simulator = get_simulator()
        simulator.clear_history()

        logger.info("Cleared simulator event history")
        return {"message": "Event history cleared"}
    except Exception as e:
        logger.error(f"Error clearing event history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulator/topology")
async def get_simulator_topology():
    """Get simulator topology."""
    try:
        simulator = get_simulator()
        topology = simulator.get_topology_summary()

        return topology
    except Exception as e:
        logger.error(f"Error getting simulator topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))
