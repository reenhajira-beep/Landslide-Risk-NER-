from typing import Any

from app.services.risk_agent import landslide_agent


class RiskAnalysisAgent:
    """
    Agent 2: Risk Analysis Agent

    Responsibilities:
    - Receive cleaned data from Agent 1
    - Run the landslide risk / ML model
    - Calculate risk score
    - Assign risk level
    - Decide alert status
    - Return explanation and actions
    """

    def analyze(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:

        result = landslide_agent.analyze(
            rainfall_mm_hr=(
                data["rainfall_mm_hr"]
            ),

            soil_moisture_pct=(
                data["soil_moisture_pct"]
            ),

            tilt_deg=(
                data["tilt_deg"]
            ),

            vegetation_change_pct=(
                data["vegetation_change_pct"]
            ),

            satellite_risk_index=(
                data["satellite_risk_index"]
            ),
        )

        return {
            **data,

            "risk_score":
                result["risk_score"],

            "risk_level":
                result["risk_level"],

            "alert_generated":
                result["alert_generated"],

            "agent_status":
                result["agent_status"],

            "contributing_factors":
                result["contributing_factors"],

            "recommended_actions":
                result["recommended_actions"],

            "analysis_message":
                result["analysis_message"],
        }


# IMPORTANT:
# This creates the object that other files import.
risk_analysis_agent = RiskAnalysisAgent()