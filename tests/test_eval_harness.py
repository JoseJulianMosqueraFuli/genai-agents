import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.harness import EvalRunner, ReleaseGate, load_eval_dataset


@pytest.mark.asyncio
async def test_eval_harness_runs_and_gates():
    runner = EvalRunner()
    results = await runner.run(load_eval_dataset())
    assert len(results) == 5

    gate = ReleaseGate(min_faithfulness=0.6, min_relevance=0.5)
    outcome = gate.evaluate(results)

    assert "passed" in outcome
    assert "avg_faithfulness" in outcome
    assert outcome["num_questions"] == 5
