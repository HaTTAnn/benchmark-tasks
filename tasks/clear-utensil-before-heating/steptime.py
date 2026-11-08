"""Optional control-step timing diagnostics.

Call tick() once per control step. When TASK_STEP_FILE is set, write simulated
elapsed time there and the slowest measured 30-step wall-time window to its
.worst30 companion file. No files are written when the variable is unset.
"""

from __future__ import annotations

import os
import time

CONTROL_HZ = 20.0
_state = {"step": 0, "mark": None, "worst": 0.0}


def _write(path: str, text: str) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def reset() -> None:
    """Clear timing records when the embodiment starts a new trial."""
    _state.update(step=0, mark=None, worst=0.0)
    path = os.environ.get("TASK_STEP_FILE")
    if path:
        _write(path, "0.00")
        _write(f"{path}.worst30", "0.00")


def tick() -> None:
    path = os.environ.get("TASK_STEP_FILE")
    if not path:
        return
    _state["step"] += 1
    step = _state["step"]
    _write(path, f"{step / CONTROL_HZ:.2f}")
    if step % 30 == 0:
        now = time.monotonic()
        if _state["mark"] is not None:
            _state["worst"] = max(_state["worst"], now - _state["mark"])
            _write(f"{path}.worst30", f"{_state['worst']:.2f}")
        _state["mark"] = now
