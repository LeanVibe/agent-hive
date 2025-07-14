# .claude/learning/confidence_optimizer.py
class ConfidenceOptimizer:
    """Learns optimal confidence thresholds over time"""

    def __init__(self):
        self.history = DecisionHistory()
        self.ml_model = ConfidencePredictor()

    def should_escalate_to_human(self, decision_context):
        """Smarter escalation based on learned patterns"""

        # Check if we've seen similar decisions before
        similar_past = self.history.find_similar(decision_context)

        if similar_past and all(d.outcome == "success" for d in similar_past[-5:]):
            # We've successfully handled this before
            return False

        # Predict outcome probability
        success_probability = self.ml_model.predict(decision_context)

        # Dynamic threshold based on risk
        risk_score = self.calculate_risk(decision_context)
        threshold = 0.9 if risk_score > 0.7 else 0.7

        return success_probability < threshold

    def record_decision_outcome(self, decision_id, human_involved, outcome):
        """Learn from every decision"""
        self.history.record(decision_id, human_involved, outcome)

        # Retrain model periodically
        if self.history.count() % 100 == 0:
            self.ml_model.retrain(self.history.get_training_data())
