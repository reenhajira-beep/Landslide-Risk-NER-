from app.services.model_service import model_service


class LandslideRiskAgent:

    def calculate_risk_level(
        self,
        score: float
    ) -> str:

        if score <= 25:
            return "LOW"

        elif score <= 50:
            return "MODERATE"

        elif score <= 75:
            return "HIGH"

        return "CRITICAL"

    def calculate_fallback_score(
        self,
        rainfall_mm_hr: float,
        soil_moisture_pct: float,
        tilt_deg: float,
        vegetation_change_pct: float,
        satellite_risk_index: float
    ) -> float:
        """
        Temporary calculation used only when the
        trained ML model is unavailable.
        """

        rainfall_score = min(
            rainfall_mm_hr / 100,
            1
        ) * 30

        moisture_score = (
            soil_moisture_pct / 100
        ) * 25

        tilt_score = min(
            tilt_deg / 10,
            1
        ) * 20

        vegetation_score = (
            vegetation_change_pct / 100
        ) * 10

        satellite_score = (
            satellite_risk_index * 15
        )

        return round(
            rainfall_score
            + moisture_score
            + tilt_score
            + vegetation_score
            + satellite_score,
            2
        )

    def analyze(
        self,
        rainfall_mm_hr: float,
        soil_moisture_pct: float,
        tilt_deg: float,
        vegetation_change_pct: float,
        satellite_risk_index: float
    ) -> dict:

        # STEP 1: Use trained ML model when loaded
        if model_service.model_loaded:

            probability = (
                model_service.predict_probability(
                    rainfall_mm_hr=rainfall_mm_hr,
                    soil_moisture_pct=(
                        soil_moisture_pct
                    ),
                    tilt_deg=tilt_deg,
                    vegetation_change_pct=(
                        vegetation_change_pct
                    ),
                    satellite_risk_index=(
                        satellite_risk_index
                    )
                )
            )

            risk_score = round(
                probability * 100,
                2
            )

            model_used = (
                "RandomForestClassifier_"
                "synthetic_prototype"
            )

            agent_status = (
                "ml_prediction_completed"
            )

        else:
            # Use fallback only when model is missing
            risk_score = (
                self.calculate_fallback_score(
                    rainfall_mm_hr,
                    soil_moisture_pct,
                    tilt_deg,
                    vegetation_change_pct,
                    satellite_risk_index
                )
            )

            model_used = (
                "temporary_rule_based_fallback"
            )

            agent_status = (
                "fallback_prediction_completed"
            )

        # STEP 2: Convert score into risk category
        risk_level = self.calculate_risk_level(
            risk_score
        )

        # STEP 3: Explain contributing factors
        contributing_factors = []

        if rainfall_mm_hr >= 40:
            contributing_factors.append(
                "Heavy rainfall detected"
            )

        if soil_moisture_pct >= 70:
            contributing_factors.append(
                "High soil saturation detected"
            )

        if tilt_deg >= 3:
            contributing_factors.append(
                "Unusual ground tilt detected"
            )

        if vegetation_change_pct >= 15:
            contributing_factors.append(
                "Significant vegetation change detected"
            )

        if satellite_risk_index >= 0.7:
            contributing_factors.append(
                "Satellite analysis indicates terrain risk"
            )

        if not contributing_factors:
            contributing_factors.append(
                "No major abnormal factor detected"
            )

        # STEP 4: Decide recommended actions
        if risk_level == "LOW":
            actions = [
                "Continue normal monitoring"
            ]

        elif risk_level == "MODERATE":
            actions = [
                "Increase monitoring frequency",
                "Notify local monitoring authorities"
            ]

        elif risk_level == "HIGH":
            actions = [
                "Generate a high-risk warning",
                "Notify disaster-management authorities",
                "Prepare nearby shelters",
                "Display warning on the dashboard"
            ]

        else:
            actions = [
                "Generate a critical warning",
                "Notify emergency authorities",
                "Activate evacuation planning",
                "Display safest shelter and route"
            ]

        # STEP 5: Return complete agent decision
        return {
            "agent_status": agent_status,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "alert_generated": risk_level in [
                "HIGH",
                "CRITICAL"
            ],
            "contributing_factors": (
                contributing_factors
            ),
            "recommended_actions": actions,
            "analysis_message": (
                f"The agent used {model_used} and "
                f"detected {risk_level.lower()} "
                f"landslide risk."
            ),
            "model_used": model_used
        }


landslide_agent = LandslideRiskAgent()